'''
接口访问路径：http://127.0.0.1:8000/docs
'''

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any
import uvicorn
import json
import asyncio
import uuid
import threading
import base64
import cv2
from pathlib import Path
import numpy as np 
import time
import hashlib
import pymysql
from datetime import datetime
import re
import asyncio
from agent.predictor import TrajectoryPredictor, estimate_distance

from agent.core import DrivingAgent
from agent.models.vehicle_tracker import VehicleTracker

# 创建FastAPI应用
app = FastAPI(title="驾驶监控Agent API", description="智能对话Agent接口")

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化Agent（单例）
agent = DrivingAgent()
tracker = None

# 存储追踪任务状态
tracking_tasks = {}

def get_tracker():
    global tracker
    if tracker is None:
        print("[API] 初始化车辆追踪器...")
        tracker = VehicleTracker(model_path="models/best.pt", show_preview=False)
        tracker.load_model()
        print("[API] 车辆追踪器初始化完成")
    return tracker

# 定义请求/响应模型
class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    memory_info: Dict[str, Any]

class MemoryInfoResponse(BaseModel):
    memory_info: Dict[str, Any]

# ========== 基础 API 路由 ==========
@app.get("/")
async def root():
    return {"message": "驾驶监控Agent API", "status": "running"}

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """对话接口"""
    try:
        response = agent.chat(request.message)
        memory_info = agent.get_memory_info()
        return ChatResponse(response=response, memory_info=memory_info)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/clear_memory")
async def clear_memory():
    agent.clear_memory()
    return {"status": "success", "message": "记忆已清空"}

@app.get("/memory_info")
async def get_memory_info():
    return agent.get_memory_info()

@app.get("/health")
async def health_check():
    return {"status": "healthy", "model": agent.model}


# ========== 视频追踪上传接口 ==========
@app.post("/track/upload")
async def upload_video_for_tracking(video: UploadFile = File(...)):
    """上传视频并开始追踪"""
    try:
        # 生成任务ID
        task_id = str(uuid.uuid4())[:8]
        
        # 保存视频文件
        video_dir = Path("uploaded_videos")
        video_dir.mkdir(exist_ok=True)
        video_path = video_dir / f"{task_id}_{video.filename}"
        
        content = await video.read()
        with open(video_path, "wb") as f:
            f.write(content)
        
        # 初始化任务状态
        tracking_tasks[task_id] = {
            "status": "processing",
            "progress": 0,
            "vehicles": [],
            "output_video": None,
            "message": "开始追踪..."
        }
        
        # 在后台线程中执行追踪
        thread = threading.Thread(
            target=run_tracking_task,
            args=(task_id, str(video_path), video.filename)
        )
        thread.start()
        
        return {
            "status": "success",
            "task_id": task_id,
            "message": "视频已上传，开始追踪"
        }
        
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/track/status/{task_id}")
async def get_tracking_status(task_id: str):
    """获取追踪状态"""
    if task_id not in tracking_tasks:
        return {"status": "error", "message": "任务不存在"}
    
    return tracking_tasks[task_id]


@app.get("/track/output/{task_id}")
async def get_tracking_output(task_id: str):
    """获取追踪输出视频"""
    task = tracking_tasks.get(task_id)
    if not task or not task.get("output_video"):
        raise HTTPException(status_code=404, detail="输出视频不存在")
    
    output_path = task["output_video"]
    if os.path.exists(output_path):
        return FileResponse(output_path, media_type="video/mp4", filename="tracked_video.mp4")
    else:
        raise HTTPException(status_code=404, detail="视频文件不存在")


def run_tracking_task(task_id: str, video_path: str, original_filename: str):
    """后台运行追踪任务"""
    try:
        # 获取追踪器
        tracker_instance = get_tracker()
        
        # 更新状态
        tracking_tasks[task_id]["message"] = "正在分析视频..."
        
        # 执行追踪
        result = tracker_instance.track_video_realtime(video_path, save_output=True)
        
        if result["status"] == "success":
            # 格式化车辆信息
            vehicles = []
            for v in result["vehicles"]:
                vehicles.append({
                    "track_id": v["track_id"],
                    "vehicle_id": v["vehicle_id"],
                    "trajectory_length": v["trajectory_length"],
                    "avg_speed": round(v["avg_speed"], 1)
                })
            
            # 输出视频路径
            output_video = Path(video_path).stem + "_tracked.mp4"
            if Path(output_video).exists():
                tracking_tasks[task_id]["output_video"] = str(Path(output_video).absolute())
            
            tracking_tasks[task_id]["status"] = "completed"
            tracking_tasks[task_id]["vehicles"] = vehicles
            tracking_tasks[task_id]["progress"] = 100
            tracking_tasks[task_id]["message"] = f"追踪完成，共检测到 {len(vehicles)} 辆车"
        else:
            tracking_tasks[task_id]["status"] = "error"
            tracking_tasks[task_id]["message"] = result.get("error", "追踪失败")
            
    except Exception as e:
        tracking_tasks[task_id]["status"] = "error"
        tracking_tasks[task_id]["message"] = str(e)
    
    # 清理临时文件
    try:
        os.remove(video_path)
    except:
        pass


# ========== WebSocket 流式接口 ==========
@app.websocket("/ws/analyze")
async def websocket_analyze(websocket: WebSocket):
    await websocket.accept()
    print("[WebSocket] 客户端已连接")
    
    try:
        while True:
            data = await websocket.receive_text()
            request = json.loads(data)
            
            message = request.get("message", "")
            video_path = request.get("video_path", "test_video.mp4")
            
            print(f"[WebSocket] 收到消息: {message[:50]}...")
            
            if "分析" in message or "视频" in message or "追踪" in message:
                await analyze_video_stream(websocket, video_path)
            else:
                response = agent.chat(message)
                await websocket.send_text(json.dumps({
                    "type": "message",
                    "content": response
                }, ensure_ascii=False))
                
    except WebSocketDisconnect:
        print("[WebSocket] 客户端断开连接")


async def analyze_video_stream(websocket: WebSocket, video_path: str):
    """流式分析视频"""
    if not os.path.exists(video_path):
        cwd = os.getcwd()
        full_path = os.path.join(cwd, video_path)
        if os.path.exists(full_path):
            video_path = full_path
        else:
            await websocket.send_text(json.dumps({
                "type": "error",
                "content": f"视频文件不存在: {video_path}"
            }, ensure_ascii=False))
            return
    
    tracker_instance = get_tracker()
    
    await websocket.send_text(json.dumps({
        "type": "status",
        "content": "🔍 开始分析视频...",
        "timestamp": 0
    }, ensure_ascii=False))
    
    result = tracker_instance.track_video_realtime(video_path, save_output=True)
    
    if result["status"] == "success":
        final_summary = f"✅ 分析完成！\n"
        final_summary += f"   - 视频时长: {result['duration']:.1f} 秒\n"
        final_summary += f"   - 检测到车辆: {result['vehicles_tracked']} 辆\n"
        
        await websocket.send_text(json.dumps({
            "type": "complete",
            "total_vehicles": result["vehicles_tracked"],
            "duration": result["duration"],
            "content": final_summary
        }, ensure_ascii=False))
    else:
        await websocket.send_text(json.dumps({
            "type": "error",
            "content": result.get("error", "追踪失败")
        }, ensure_ascii=False))


@app.websocket("/ws/track1")
async def websocket_track1(websocket: WebSocket):
    await websocket.accept()
    print("[WebSocket] 追踪客户端已连接")
    
    try:
        # 接收前端发来的消息（包含视频路径和开始时间）
        data = await asyncio.wait_for(websocket.receive_text(), timeout=30)
        request = json.loads(data)
        video_path = request.get("video_path", "test_video.mp4")
        start_time = request.get("start_time", 0)
        
        print(f"[WebSocket] 视频路径: {video_path}, 开始时间: {start_time:.1f}秒")
        
        # 获取追踪器
        tracker = get_tracker()
        tracker.show_preview = False
        
        # 检查视频文件是否存在
        if not os.path.exists(video_path):
            alt_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), video_path)
            if os.path.exists(alt_path):
                video_path = alt_path
            else:
                await websocket.send_text(json.dumps({"type": "error", "message": f"视频文件不存在: {video_path}"}))
                return
        
        # 打开视频
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            await websocket.send_text(json.dumps({"type": "error", "message": f"无法打开视频: {video_path}"}))
            return
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        # 计算从哪一帧开始
        start_frame = int(start_time * fps)
        start_frame = max(0, min(start_frame, total_frames - 1))
        cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
        
        print(f"[WebSocket] 视频总帧数: {total_frames}, 从第 {start_frame} 帧开始")
        
        # 发送开始消息
        await websocket.send_text(json.dumps({
            "type": "start",
            "total_frames": int(total_frames),
            "fps": float(fps),
            "start_time": float(start_time)
        }))
        
        all_track_ids = set()
        # 存储轨迹点（用于过滤）
        trajectories = {}
        frame_idx = start_frame
        
        # 处理参数
        process_every_n = 3
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            
            # 跳帧处理
            if (frame_idx - start_frame) % process_every_n == 0:
                # YOLO 追踪
                results = tracker.model.track(frame, persist=True, verbose=False, device=tracker.device, tracker="configs/botsort_custom.yaml")
                
                # 绘制检测框
                if results[0].boxes is not None and results[0].boxes.id is not None:
                    boxes = results[0].boxes.xyxy.cpu().numpy()
                    track_ids = results[0].boxes.id.cpu().numpy().astype(int)
                    
                    for box, track_id in zip(boxes, track_ids):
                        x1, y1, x2, y2 = map(int, box)
                        center_x = (x1 + x2) / 2
                        center_y = (y1 + y2) / 2
                        color = tracker.get_color(track_id)
                        
                        # 记录轨迹点
                        point = {
                            "frame": frame_idx,
                            "timestamp": frame_idx / fps if fps > 0 else frame_idx,
                            "x": center_x,
                            "y": center_y
                        }
                        
                        if track_id not in trajectories:
                            trajectories[track_id] = []
                        trajectories[track_id].append(point)
                        
                        # 绘制矩形框
                        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                        # 绘制ID标签背景
                        label = str(track_id)
                        (label_w, label_h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
                        cv2.rectangle(frame, (x1, y1 - label_h - 5), (x1 + label_w + 5, y1), color, -1)
                        cv2.putText(frame, label, (x1 + 2, y1 - 5), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                        
                        # 新车检测
                        if int(track_id) not in all_track_ids:
                            all_track_ids.add(int(track_id))
                            await websocket.send_text(json.dumps({
                                "type": "new_vehicle",
                                "vehicle_id": int(track_id),
                                "count": int(len(all_track_ids))
                            }))
                            await asyncio.sleep(0.01)
                
                # 压缩图像质量
                encode_param = [cv2.IMWRITE_JPEG_QUALITY, 50]
                _, buffer = cv2.imencode('.jpg', frame, encode_param)
                frame_base64 = base64.b64encode(buffer).decode('utf-8')
                
                # 计算进度
                current_frame = frame_idx - start_frame
                remaining_frames = total_frames - start_frame
                progress_pct = int(current_frame / remaining_frames * 100) if remaining_frames > 0 else 0
                
                # 推送帧数据
                try:
                    await websocket.send_text(json.dumps({
                        "type": "frame",
                        "image": frame_base64,
                        "frame": int(frame_idx),
                        "progress": int(progress_pct),
                        "vehicles": int(len(all_track_ids))
                    }))
                except Exception as e:
                    print(f"发送帧失败: {e}")
                    break
                
                await asyncio.sleep(0.03)
            
            frame_idx += 1
        
        cap.release()
        
        filtered_vehicles = []
        for track_id, points in trajectories.items():
            if len(points) >= 3:
                filtered_vehicles.append(track_id)
        
        print(f"[WebSocket] 原始车辆数: {len(trajectories)}, 过滤后: {len(filtered_vehicles)}")
        
        # 发送完成消息（使用过滤后的数量）
        await websocket.send_text(json.dumps({
            "type": "complete",
            "vehicles": len(filtered_vehicles),
            "total_detected": len(trajectories),
            "filtered": len(trajectories) - len(filtered_vehicles)
        }))
        
    except asyncio.TimeoutError:
        print("[WebSocket] 接收消息超时")
        try:
            await websocket.send_text(json.dumps({"type": "error", "message": "接收消息超时"}))
        except:
            pass
    except Exception as e:
        print(f"[WebSocket] 错误: {e}")
        try:
            await websocket.send_text(json.dumps({"type": "error", "message": str(e)}))
        except:
            pass
    finally:
        try:
            await websocket.close()
        except:
            pass


@app.websocket("/ws/track2")
async def websocket_track2(websocket: WebSocket):
    await websocket.accept()
    print("[WebSocket] 追踪客户端已连接")
    
    # 停止标志
    stop_tracking = False
    
    # 监听停止消息
    async def listen_for_stop():
        nonlocal stop_tracking
        try:
            msg = await websocket.receive_text()
            if msg == "stop" or msg == '{"action":"stop"}':
                stop_tracking = True
                print("[WebSocket] 收到停止信号")
                await websocket.send_text(json.dumps({
                    "type": "stopped",
                    "message": "追踪已停止"
                }))
        except Exception as e:
            print(f"监听停止信号出错: {e}")
    
    try:
        # 接收前端发来的消息
        data = await asyncio.wait_for(websocket.receive_text(), timeout=30)
        request = json.loads(data)
        video_path = request.get("video_path", "test_video.mp4")
        start_time = request.get("start_time", 0)
        user_id = request.get("user_id", None)
        
        print(f"[WebSocket] 视频路径: {video_path}, 开始时间: {start_time:.1f}秒, 用户ID: {user_id}")
        
        # 获取追踪器
        tracker = get_tracker()
        tracker.show_preview = False
        
        # 检查视频文件是否存在
        if not os.path.exists(video_path):
            alt_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), video_path)
            if os.path.exists(alt_path):
                video_path = alt_path
            else:
                await websocket.send_text(json.dumps({"type": "error", "message": f"视频文件不存在: {video_path}"}))
                return
        
        # 打开视频
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            await websocket.send_text(json.dumps({"type": "error", "message": f"无法打开视频: {video_path}"}))
            return
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        # 画面中心点
        CENTER_X = frame_width // 2
        CENTER_Y = frame_height // 2
        
        # 计算从哪一帧开始
        start_frame = int(start_time * fps)
        start_frame = max(0, min(start_frame, total_frames - 1))
        cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
        
        print(f"[WebSocket] 视频总帧数: {total_frames}, 从第 {start_frame} 帧开始")
        
        # 发送开始消息
        await websocket.send_text(json.dumps({
            "type": "start",
            "total_frames": int(total_frames),
            "fps": float(fps),
            "start_time": float(start_time)
        }))
        
        all_track_ids = set()
        frame_idx = start_frame
        
        # 速度记录
        vehicle_speeds = {}
        
        # 告警冷却时间记录
        last_alert_time = {}
        
        # AI 分析相关变量
        last_ai_analysis_time = time.time()
        ai_analysis_interval = 5.0
        
        # 轨迹预测器 
        trajectory_predictor = TrajectoryPredictor(trail_len=30, predict_steps=10)
        
        # 性能优化参数
        process_every_n = 4
        frame_quality = 40
        target_frame_interval = 1.0 / 8
        
        last_send_time = time.time()
        
        # 启动监听停止信号的协程
        stop_listener = asyncio.create_task(listen_for_stop())
        
        while cap.isOpened():
            if stop_tracking:
                print("[追踪] 用户停止追踪，正在退出...")
                break
            
            ret, frame = cap.read()
            if not ret:
                break
            
            current_time = time.time()
            
            if current_time - last_send_time < target_frame_interval:
                frame_idx += 1
                continue
            
            if (frame_idx - start_frame) % process_every_n == 0:
                timestamp = frame_idx / fps if fps > 0 else 0
                
                results = tracker.model.track(frame, persist=True, verbose=False, device=tracker.device, tracker="configs/botsort_custom.yaml")
                
                current_vehicles = []
                active_ids = set()
                
                if results[0].boxes is not None and results[0].boxes.id is not None:
                    boxes = results[0].boxes.xyxy.cpu().numpy()
                    track_ids = results[0].boxes.id.cpu().numpy().astype(int)
                    
                    if len(boxes) == 0 or len(track_ids) == 0:
                        continue
                    
                    for box, track_id in zip(boxes, track_ids):
                        try:
                            x1, y1, x2, y2 = map(int, box)
                            center_x = (x1 + x2) / 2
                            center_y = (y1 + y2) / 2
                            color = tracker.get_color(track_id)
                            tid = int(track_id)
                            active_ids.add(tid)
                            
                            if tid not in vehicle_speeds:
                                vehicle_speeds[tid] = []
                            
                            vehicle_speeds[tid].append({
                                "timestamp": timestamp,
                                "x": center_x,
                                "y": center_y
                            })
                            
                            if len(vehicle_speeds[tid]) > 30:
                                vehicle_speeds[tid] = vehicle_speeds[tid][-30:]
                            
                            # 计算当前速度
                            current_speed = 0
                            if len(vehicle_speeds[tid]) >= 3:
                                recent = vehicle_speeds[tid][-3:]
                                if len(recent) >= 2:
                                    dt = recent[-1]["timestamp"] - recent[-2]["timestamp"]
                                    if dt > 0:
                                        dx = recent[-1]["x"] - recent[-2]["x"]
                                        dy = recent[-1]["y"] - recent[-2]["y"]
                                        current_speed = np.sqrt(dx**2 + dy**2) / dt
                            
                            # 收集车辆数据
                            if current_speed > 0:
                                vehicle_data = {
                                    "id": tid,
                                    "speed": round(current_speed, 1),
                                    "x": round(center_x, 1),
                                    "y": round(center_y, 1),
                                    "bbox": [x1, y1, x2, y2],
                                    "distance_to_center": round(np.sqrt((center_x - CENTER_X)**2 + (center_y - CENTER_Y)**2), 1)
                                }
                                
                                # 轨迹预测更新
                                prediction = trajectory_predictor.update(tid, center_x, center_y)
                                vehicle_data["predicted_positions"] = prediction["predicted_positions"]
                                vehicle_data["velocity"] = prediction["velocity"]
                                vehicle_data["pred_speed"] = prediction["speed"]
                                
                                # ========== 告警1: 速度告警 ==========
                                speed = vehicle_data["speed"]
                                last_time = last_alert_time.get(f"speed_{tid}", 0)
                                if current_time - last_time >= 5:
                                    if speed > 160:
                                        alert_msg = f"车辆{tid}严重超速({speed:.0f})"
                                        last_alert_time[f"speed_{tid}"] = current_time
                                        await websocket.send_text(json.dumps({
                                            "type": "agent_warning",
                                            "message": f"🚨 {alert_msg}",
                                            "severity": "danger",
                                            "timestamp": timestamp
                                        }))
                                        print(f"[速度告警] {alert_msg}")
                                        asyncio.create_task(save_alarm_to_db({
                                            "alarm_type": "speeding",
                                            "alarm_level": 1,
                                            "info": alert_msg,
                                            "vehicle_id": str(tid),
                                            "video_name": os.path.basename(video_path)
                                        }, user_id))
                                    elif speed > 120:
                                        alert_msg = f"车辆{tid}超速({speed:.0f})"
                                        last_alert_time[f"speed_{tid}"] = current_time
                                        await websocket.send_text(json.dumps({
                                            "type": "agent_warning",
                                            "message": f"⚠️ {alert_msg}",
                                            "severity": "warning",
                                            "timestamp": timestamp
                                        }))
                                        print(f"[速度告警] {alert_msg}")
                                        asyncio.create_task(save_alarm_to_db({
                                            "alarm_type": "speeding",
                                            "alarm_level": 2,
                                            "info": alert_msg,
                                            "vehicle_id": str(tid),
                                            "video_name": os.path.basename(video_path)
                                        }, user_id))
                                
                                # ========== 告警2: 综合告警（中心位置 + 距离） ==========
                                distance_to_center = vehicle_data["distance_to_center"]
                                box_width = x2 - x1
                                distance = estimate_distance(box_width, frame_width, 1.8, 60)
                                
                                if distance_to_center < 150 and distance and distance < 30:
                                    last_time = last_alert_time.get(f"combo_{tid}", 0)
                                    if current_time - last_time >= 5:
                                        last_alert_time[f"combo_{tid}"] = current_time
                                        if distance < 15:
                                            alert_msg = f"车辆{tid} 正前方 {distance:.0f}米！碰撞风险！"
                                            severity = "danger"
                                            alarm_level = 1
                                        else:
                                            alert_msg = f"车辆{tid} 正前方 {distance:.0f}米，注意车距"
                                            severity = "warning"
                                            alarm_level = 2
                                        
                                        await websocket.send_text(json.dumps({
                                            "type": "agent_warning",
                                            "message": f"⚠️ {alert_msg}",
                                            "severity": severity,
                                            "timestamp": timestamp
                                        }))
                                        print(f"[综合告警] {alert_msg}")
                                        
                                        # 保存到数据库
                                        asyncio.create_task(save_alarm_to_db({
                                            "alarm_type": "collision_risk",
                                            "alarm_level": alarm_level,
                                            "info": alert_msg,
                                            "vehicle_id": str(tid),
                                            "video_name": os.path.basename(video_path)
                                        }, user_id))
                                
                                current_vehicles.append(vehicle_data)
                            
                            # 绘制矩形框
                            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                            
                            if current_speed > 120:
                                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 3)
                            
                            # 绘制预测轨迹点
                            if 'prediction' in locals() and prediction["predicted_positions"]:
                                for i, (px, py) in enumerate(prediction["predicted_positions"]):
                                    cv2.circle(frame, (px, py), 3, (0, 255, 255), -1)
                            
                            # ID标签
                            label = str(track_id)
                            cv2.putText(frame, label, (x1 + 4, y1 - 4), 
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                            
                            if tid not in all_track_ids:
                                all_track_ids.add(tid)
                                await websocket.send_text(json.dumps({
                                    "type": "new_vehicle",
                                    "vehicle_id": tid,
                                    "count": int(len(all_track_ids))
                                }))
                                await asyncio.sleep(0.005)
                            
                        except Exception as e:
                            print(f"处理检测框时出错: {e}")
                            continue
                
                # 清理不活跃的车辆
                trajectory_predictor.cleanup(active_ids)
                
                # ========== 告警3: 变道告警 ==========
                if current_time - last_ai_analysis_time >= ai_analysis_interval and len(current_vehicles) > 0:
                    last_ai_analysis_time = current_time
                    
                    # 为 AI 准备带轨迹数据的车辆信息
                    vehicles_for_analysis = []
                    for v in current_vehicles[:10]:
                        tid = v["id"]
                        trajectory = trajectory_predictor.get_trajectory(tid)
                        if len(trajectory) >= 5:
                            v["trajectory"] = trajectory[-10:]
                            vehicles_for_analysis.append(v)
                    
                    if len(vehicles_for_analysis) > 0:
                        analysis_data = {
                            "timestamp": round(timestamp, 1),
                            "vehicles": vehicles_for_analysis
                        }
                        
                        prompt = f"""分析车辆轨迹数据，判断是否有车辆正在变道：

{json.dumps(analysis_data, ensure_ascii=False)}

规则：
- 有车辆变道：只输出"车辆[ID]变道"
- 没有变道：什么都不输出

严格禁止输出任何解释、分析、速度、建议。"""
                        
                        try:
                            loop = asyncio.get_event_loop()
                            analysis_result = await loop.run_in_executor(None, agent.chat, prompt)
                            
                            if analysis_result and analysis_result.strip():
                                normal_keywords = ["一切正常", "正常", "未触发", "没有触发", "无异常"]
                                is_normal = any(kw in analysis_result for kw in normal_keywords)
                                
                                if not is_normal and ("变道" in analysis_result or "车辆" in analysis_result):
                                    vehicle_id_match = re.search(r'车辆?(\d+)', analysis_result)
                                    vehicle_id = vehicle_id_match.group(1) if vehicle_id_match else None
                                    
                                    short_msg = analysis_result[:30]
                                    
                                    await websocket.send_text(json.dumps({
                                        "type": "agent_warning",
                                        "message": f"🤖 {short_msg}",
                                        "severity": "warning",
                                        "timestamp": timestamp
                                    }))
                                    print(f"[AI变道告警] {short_msg}")
                                    
                                    asyncio.create_task(save_alarm_to_db({
                                        "alarm_type": "ai_analysis",
                                        "alarm_level": 2,
                                        "info": short_msg,
                                        "vehicle_id": vehicle_id,
                                        "video_name": os.path.basename(video_path)
                                    }, user_id))
                        except Exception as e:
                            print(f"AI分析出错: {e}")
                
                # 压缩图像
                encode_param = [cv2.IMWRITE_JPEG_QUALITY, frame_quality]
                _, buffer = cv2.imencode('.jpg', frame, encode_param)
                frame_base64 = base64.b64encode(buffer).decode('utf-8')
                
                current_frame = frame_idx - start_frame
                remaining_frames = total_frames - start_frame
                progress_pct = int(current_frame / remaining_frames * 100) if remaining_frames > 0 else 0
                
                try:
                    await websocket.send_text(json.dumps({
                        "type": "frame",
                        "image": frame_base64,
                        "progress": int(progress_pct),
                        "vehicles": int(len(all_track_ids))
                    }))
                    last_send_time = current_time
                except Exception as e:
                    print(f"发送帧失败: {e}")
                    break
            
            frame_idx += 1
        
        cap.release()
        
        if not stop_tracking:
            await websocket.send_text(json.dumps({
                "type": "complete",
                "vehicles": int(len(all_track_ids))
            }))
        
        stop_listener.cancel()
        
    except asyncio.TimeoutError:
        print("[WebSocket] 接收消息超时")
        try:
            await websocket.send_text(json.dumps({"type": "error", "message": "接收消息超时"}))
        except:
            pass
    except Exception as e:
        print(f"[WebSocket] 错误: {e}")
        try:
            await websocket.send_text(json.dumps({"type": "error", "message": str(e)}))
        except:
            pass
    finally:
        try:
            await websocket.close()
        except:
            pass


@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """流式对话 WebSocket"""
    await websocket.accept()
    print("[WebSocket] 流式对话客户端已连接")
    
    try:
        while True:
            # 接收用户消息
            data = await websocket.receive_text()
            request = json.loads(data)
            message = request.get("message", "")
            
            print(f"[WebSocket] 收到对话消息: {message[:50]}...")
            
            # 调用 Agent 获取回复
            response = agent.chat(message)
            
            # 逐字发送（模拟打字效果）
            for i, char in enumerate(response):
                await websocket.send_text(json.dumps({
                    "type": "chunk",
                    "content": char,
                    "index": i,
                    "total": len(response)
                }))
                await asyncio.sleep(0.02)  # 20ms 延迟，模拟打字
            
            # 发送结束标记
            await websocket.send_text(json.dumps({
                "type": "end",
                "full_content": response
            }))
            
    except WebSocketDisconnect:
        print("[WebSocket] 流式对话客户端断开连接")
    except Exception as e:
        print(f"[WebSocket] 错误: {e}")

# 数据库配置
DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': 'xxxx',
    'database': 'driving_agent_db',
    'charset': 'utf8mb4'
}

def get_db_connection():
    return pymysql.connect(**DB_CONFIG)

def hash_password(password: str) -> str:
    return hashlib.md5(password.encode()).hexdigest()

# 注册及登录
class RegisterRequest(BaseModel):
    username: str
    password: str
    email: Optional[str] = None

class LoginRequest(BaseModel):
    username: str
    password: str

@app.post("/api/register")
async def register(request: RegisterRequest):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 检查用户名是否存在
        cursor.execute("SELECT id FROM users WHERE username = %s", (request.username,))
        if cursor.fetchone():
            return {"success": False, "message": "用户名已存在"}
        
        # 检查邮箱是否存在
        if request.email:
            cursor.execute("SELECT id FROM users WHERE email = %s", (request.email,))
            if cursor.fetchone():
                return {"success": False, "message": "邮箱已被注册"}
        
        # 插入新用户
        password_hash = hash_password(request.password)
        cursor.execute(
            "INSERT INTO users (username, password, email) VALUES (%s, %s, %s)",
            (request.username, password_hash, request.email)
        )
        conn.commit()
        
        return {"success": True, "message": "注册成功", "user": {"username": request.username}}
    except Exception as e:
        conn.rollback()
        return {"success": False, "message": f"注册失败: {str(e)}"}
    finally:
        cursor.close()
        conn.close()

@app.post("/api/login")
async def login(request: LoginRequest):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "SELECT id, username, email, password FROM users WHERE username = %s",
            (request.username,)
        )
        user = cursor.fetchone()
        
        if not user:
            return {"success": False, "message": "用户名不存在"}
        
        user_id, username, email, password_hash = user
        
        if hash_password(request.password) != password_hash:
            return {"success": False, "message": "密码错误"}
        
        # 生成 token
        token = hashlib.md5(f"{username}_{time.time()}".encode()).hexdigest()
        
        return {
            "success": True,
            "message": "登录成功",
            "token": token,
            "user": {"id": user_id, "username": username, "email": email}
        }
    except Exception as e:
        return {"success": False, "message": f"登录失败: {str(e)}"}
    finally:
        cursor.close()
        conn.close()

# 告警
class AlarmRecord(BaseModel):
    alarm_type: str
    alarm_level: int = 2  # 1-紧急, 2-严重, 3-一般
    info: str
    vehicle_id: Optional[str] = None
    video_name: Optional[str] = None
    user_id: Optional[int] = None

@app.post("/api/alarms")
async def save_alarm(record: AlarmRecord):
    """保存告警记录"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO alarm_records (alarm_type, alarm_level, info, vehicle_id, video_name, user_id, trigger_time)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            record.alarm_type,
            record.alarm_level,
            record.info,
            record.vehicle_id,
            record.video_name,
            record.user_id,
            datetime.now()
        ))
        conn.commit()
        record_id = cursor.lastrowid
        return {"success": True, "message": "告警记录已保存", "id": record_id}
    except Exception as e:
        conn.rollback()
        return {"success": False, "message": f"保存失败: {str(e)}"}
    finally:
        cursor.close()
        conn.close()


@app.get("/api/alarms")
async def get_alarms(limit: int = 100, user_id: Optional[int] = None):
    """获取告警历史记录（只返回当前用户的）"""
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    
    try:
        if user_id:
            cursor.execute("""
                SELECT id, alarm_type, alarm_level, info, vehicle_id, video_name, trigger_time
                FROM alarm_records
                WHERE user_id = %s
                ORDER BY trigger_time DESC
                LIMIT %s
            """, (user_id, limit))
        else:
            # 没有 user_id 时返回空列表
            return []
        
        records = cursor.fetchall()
        
        result = []
        for row in records:
            result.append({
                "id": row["id"],
                "alarm_type": row["alarm_type"],
                "alarm_level": row["alarm_level"],
                "info": row["info"],
                "vehicle_id": row["vehicle_id"],
                "video_name": row["video_name"],
                "trigger_time": row["trigger_time"].strftime("%Y-%m-%d %H:%M:%S") if row["trigger_time"] else None
            })
        
        return result
    except Exception as e:
        print(f"获取告警记录失败: {e}")
        return []
    finally:
        cursor.close()
        conn.close()


@app.delete("/api/alarms/clear")
async def clear_all_alarms():
    """清空所有告警记录"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("TRUNCATE TABLE alarm_records")
        conn.commit()
        return {"success": True, "message": "已清空所有告警记录"}
    except Exception as e:
        conn.rollback()
        return {"success": False, "message": f"清空失败: {str(e)}"}
    finally:
        cursor.close()
        conn.close()


@app.delete("/api/alarms/{alarm_id}")
async def delete_alarm(alarm_id: int):
    """删除单条告警记录"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("DELETE FROM alarm_records WHERE id = %s", (alarm_id,))
        conn.commit()
        if cursor.rowcount > 0:
            return {"success": True, "message": "删除成功"}
        else:
            return {"success": False, "message": "记录不存在"}
    except Exception as e:
        conn.rollback()
        return {"success": False, "message": f"删除失败: {str(e)}"}
    finally:
        cursor.close()
        conn.close()


async def save_alarm_to_db(alarm_data: dict, user_id: int = None):
    """异步保存告警到数据库（供 WebSocket 调用）"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO alarm_records (alarm_type, alarm_level, info, vehicle_id, video_name, user_id, trigger_time)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            alarm_data.get("alarm_type", "unknown"),
            alarm_data.get("alarm_level", 2),
            alarm_data.get("info", ""),
            alarm_data.get("vehicle_id"),
            alarm_data.get("video_name"),
            user_id,
            datetime.now()
        ))
        conn.commit()
        print(f"[数据库] 告警记录已保存: {alarm_data.get('info', '')[:50]}")
    except Exception as e:
        print(f"[数据库] 保存告警失败: {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
