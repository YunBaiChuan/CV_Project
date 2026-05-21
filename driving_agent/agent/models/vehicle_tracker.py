"""
车辆追踪模块 - 基于 YOLOv8 自带追踪
只负责追踪和数据收集，告警由 WebSocket 处理
支持 ReID 增强追踪
"""
import cv2
import torch
import numpy as np
from ultralytics import YOLO
from typing import Dict, List, Optional, Tuple, Callable
from pathlib import Path
import time
import os

class VehicleTracker:
    """基于YOLOv8的车辆追踪器 - 使用自带追踪，支持 ReID"""
    
    def __init__(self, model_path: str = "models/best.pt", show_preview: bool = False):
        self.model_path = Path(model_path)
        self.model = None
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.show_preview = show_preview
        
        # ReID 配置文件路径
        self.tracker_config = "configs/botsort_custom.yaml"
        
        # 颜色映射
        self.colors = {}
        self.next_color_idx = 0
        self.color_palette = [
            (255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0),
            (255, 0, 255), (0, 255, 255), (128, 0, 128), (255, 128, 0),
            (0, 128, 255), (128, 255, 0), (255, 0, 128), (0, 255, 128)
        ]
        
        if not self.model_path.exists():
            raise FileNotFoundError(f"模型文件不存在: {self.model_path.absolute()}")
        
        # 检查配置文件
        config_path = Path(self.tracker_config)
        if not config_path.exists():
            print(f"[Tracker] 警告: 配置文件不存在: {config_path}")
            print(f"[Tracker] 将使用默认追踪器")
        
        print(f"[Tracker] 初始化完成，设备: {self.device}")
        print(f"[Tracker] 实时预览: {'开启' if show_preview else '关闭'}")
        print(f"[Tracker] ReID 配置: {self.tracker_config if config_path.exists() else '未启用'}")
    
    def load_model(self):
        """加载YOLO模型"""
        if self.model is None:
            print(f"[Tracker] 加载模型: {self.model_path}")
            self.model = YOLO(str(self.model_path))
            print(f"[Tracker] 模型加载成功 ✅")
    
    def get_color(self, track_id: int) -> Tuple[int, int, int]:
        """为车辆分配颜色"""
        if track_id not in self.colors:
            self.colors[track_id] = self.color_palette[self.next_color_idx % len(self.color_palette)]
            self.next_color_idx += 1
        return self.colors[track_id]
    
    def track_video_realtime(self, video_path: str, save_output: bool = False, stop_flag: Optional[Callable[[], bool]] = None) -> Dict:
        """
        实时追踪视频 - 使用YOLOv8自带追踪
        只负责追踪，不处理告警（告警由 WebSocket 处理）
        
        Args:
            video_path: 视频文件路径
            save_output: 是否保存输出视频（默认 False，不保存）
            stop_flag: 可选的停止标志函数，返回True时停止追踪
        """
        if self.model is None:
            self.load_model()
        
        print(f"[Tracker] 开始追踪: {video_path}")
        
        # 打开视频
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return {"status": "error", "error": f"无法打开视频: {video_path}"}
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        print(f"[Tracker] 视频信息: {total_frames}帧, {fps}fps, {frame_width}x{frame_height}")
        
        # 准备输出视频（默认不保存）
        out = None
        if save_output:
            output_path = Path(video_path).stem + "_tracked.mp4"
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(str(output_path), fourcc, fps, (frame_width, frame_height))
            print(f"[Tracker] 输出视频: {output_path}")
        
        # 存储数据
        all_trajectories = {}
        frame_idx = 0
        start_time = time.time()
        last_progress_time = time.time()
        
        # 显示窗口
        if self.show_preview:
            cv2.namedWindow('Vehicle Tracking', cv2.WINDOW_NORMAL)
            display_width = min(frame_width, 1280)
            display_height = int(frame_height * display_width / frame_width)
            cv2.resizeWindow('Vehicle Tracking', display_width, display_height)
        
        print(f"\n{'='*50}")
        print(f"🔍 开始分析视频...")
        print(f"   视频时长: {total_frames/fps:.1f} 秒")
        print(f"{'='*50}\n")
        
        while cap.isOpened():
            if stop_flag and stop_flag():
                print(f"\n[Tracker] 收到停止信号，中断追踪")
                break
            
            ret, frame = cap.read()
            if not ret:
                break
            
            # YOLO 追踪 - 使用 ReID 配置文件
            config_path = Path(self.tracker_config)
            if config_path.exists():
                results = self.model.track(
                    frame,
                    persist=True,
                    verbose=False,
                    device=self.device,
                    tracker=self.tracker_config
                )
            else:
                results = self.model.track(
                    frame,
                    persist=True,
                    verbose=False,
                    device=self.device
                )
            
            # 提取追踪结果
            if results[0].boxes is not None and results[0].boxes.id is not None:
                boxes = results[0].boxes.xyxy.cpu().numpy()
                track_ids = results[0].boxes.id.cpu().numpy().astype(int)
                confs = results[0].boxes.conf.cpu().numpy()
                
                for box, track_id, conf in zip(boxes, track_ids, confs):
                    x1, y1, x2, y2 = map(int, box)
                    center_x = (x1 + x2) / 2
                    center_y = (y1 + y2) / 2
                    color = self.get_color(track_id)
                    timestamp = frame_idx / fps
                    
                    # 计算当前速度
                    current_speed = 0
                    if track_id in all_trajectories and len(all_trajectories[track_id]) >= 3:
                        recent = all_trajectories[track_id][-3:]
                        if len(recent) >= 2:
                            dt = timestamp - recent[-1]["timestamp"]
                            if dt > 0:
                                dx = center_x - recent[-1]["position"]["x"]
                                dy = center_y - recent[-1]["position"]["y"]
                                current_speed = np.sqrt(dx**2 + dy**2) / dt
                    
                    # 记录轨迹点（包含速度）
                    point = {
                        "frame": frame_idx,
                        "timestamp": timestamp,
                        "position": {"x": float(center_x), "y": float(center_y)},
                        "bbox": [float(x1), float(y1), float(x2), float(y2)],
                        "speed": float(current_speed)
                    }
                    
                    # 新车检测
                    if track_id not in all_trajectories:
                        all_trajectories[track_id] = []
                        print(f"[{timestamp:.1f}s] 🚗 检测到第 {len(all_trajectories)} 辆车 (ID:{track_id})")
                    
                    all_trajectories[track_id].append(point)
                    
                    # ========== 可视化 ==========
                    # 绘制矩形框
                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                    
                    # ID标签
                    label = f"{track_id}"
                    font = cv2.FONT_HERSHEY_DUPLEX
                    font_scale = 0.8
                    font_thickness = 2
                    
                    (label_w, label_h), _ = cv2.getTextSize(label, font, font_scale, font_thickness)
                    
                    label_x = x1
                    label_y = y1 - 8
                    if label_y - label_h < 0:
                        label_y = y1 + label_h + 8
                    
                    bg_radius = max(label_w, label_h) // 2 + 5
                    cv2.circle(frame, (label_x + label_w // 2, label_y - label_h // 2), 
                              bg_radius, color, -1)
                    cv2.putText(frame, label, (label_x, label_y), font, font_scale,
                               (255, 255, 255), font_thickness, cv2.LINE_AA)
            
            # 进度显示
            current_time_val = time.time()
            if current_time_val - last_progress_time >= 2.0:
                progress = frame_idx / total_frames
                timestamp = frame_idx / fps
                print(f"[{timestamp:.1f}s] 📊 分析进度: {progress*100:.0f}% ({frame_idx}/{total_frames}帧), 已发现 {len(all_trajectories)} 辆车")
                last_progress_time = current_time_val
            
            # 信息栏
            info_text = f"Vehicles: {len(all_trajectories)} | Frame: {frame_idx}/{total_frames}"
            (info_w, info_h), _ = cv2.getTextSize(info_text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            cv2.rectangle(frame, (5, 5), (info_w + 15, info_h + 15), (0, 0, 0), -1)
            cv2.putText(frame, info_text, (10, info_h + 12), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            
            # 保存输出
            if save_output and out:
                out.write(frame)
            
            # 实时显示
            if self.show_preview:
                if frame_width > 1280:
                    scale = 1280 / frame_width
                    display_h = int(frame_height * scale)
                    display_frame = cv2.resize(frame, (1280, display_h))
                else:
                    display_frame = frame
                cv2.imshow('Vehicle Tracking', display_frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            
            frame_idx += 1
        
        cap.release()
        if save_output and out:
            out.release()
        if self.show_preview:
            cv2.destroyAllWindows()
        
        # 最终统计
        elapsed = time.time() - start_time
        
        print(f"\n{'='*50}")
        if stop_flag and stop_flag():
            print(f"⏹️ 追踪已提前停止!")
        else:
            print(f"✅ 分析完成!")
        print(f"   - 已处理帧数: {frame_idx}/{total_frames}")
        print(f"   - 检测到车辆: {len(all_trajectories)} 辆")
        print(f"   - 处理时间: {elapsed:.1f} 秒")
        print(f"{'='*50}\n")
        
        return self._format_result(video_path, all_trajectories, fps, total_frames)
    
    def _format_result(self, video_path: str, trajectories: Dict, fps: float, total_frames: int) -> Dict:
        """格式化结果 - 包含速度信息"""
        formatted_vehicles = []
        
        for track_id, points in trajectories.items():
            if len(points) < 3:
                continue
            
            # 从轨迹点中提取速度
            speeds = []
            for p in points:
                speed = p.get("speed", 0)
                if speed > 0:
                    speeds.append(speed)
            
            avg_speed = np.mean(speeds) if speeds else 0
            
            formatted_vehicles.append({
                "track_id": int(track_id),
                "vehicle_id": f"vehicle_{track_id}",
                "trajectory_length": len(points),
                "avg_speed": float(avg_speed)
            })
        
        return {
            "status": "success",
            "video_path": video_path,
            "duration": total_frames / fps if fps > 0 else 0,
            "vehicles_tracked": len(formatted_vehicles),
            "vehicles": formatted_vehicles
        }


# 测试
if __name__ == "__main__":
    import os
    
    tracker = VehicleTracker(model_path="models/best.pt", show_preview=True)
    tracker.load_model()
    
    test_video = "val_video.mp4"
    if os.path.exists(test_video):
        result = tracker.track_video_realtime(test_video, save_output=False)
        print(f"\n✅ 追踪完成!")
        print(f"   追踪到 {result['vehicles_tracked']} 辆车")
    else:
        print(f"未找到测试视频: {test_video}")