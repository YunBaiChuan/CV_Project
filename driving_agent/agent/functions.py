"""
Agent Function Calling 函数库
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from typing import Dict, Any
from datetime import datetime

from agent.models.vehicle_tracker import VehicleTracker

_tracker = None

def get_tracker():
    global _tracker
    if _tracker is None:
        print("[Function] 初始化车辆追踪器...")
        _tracker = VehicleTracker(model_path="models/best.pt", show_preview=True)  # 开启预览
        _tracker.load_model()
        print("[Function] 车辆追踪器初始化完成")
    return _tracker


def track_vehicle(video_path: str) -> Dict[str, Any]:
    """追踪视频中的车辆 - 调用 VehicleTracker 的追踪方法"""
    print(f"[Function] 调用 track_vehicle: {video_path}")
    
    # 检查文件是否存在
    if not os.path.exists(video_path):
        cwd = os.getcwd()
        full_path = os.path.join(cwd, video_path)
        if os.path.exists(full_path):
            video_path = full_path
            print(f"[Function] 使用完整路径: {video_path}")
        else:
            return {
                "status": "error",
                "message": f"视频文件不存在: {video_path}"
            }
    
    try:
        tracker = get_tracker()
        # 调用追踪器的方法（包含预览窗口、控制台输出）
        result = tracker.track_video_realtime(video_path, save_output=True)
        
        if result["status"] == "success":
            vehicles_summary = []
            for v in result["vehicles"][:20]:
                vehicles_summary.append({
                    "vehicle_id": v["vehicle_id"],
                    "track_id": v["track_id"],
                    "trajectory_length": v["trajectory_length"],
                    "avg_speed": round(v.get("avg_speed", 0), 1)
                })
            
            return {
                "status": "success",
                "message": f"成功追踪到 {result['vehicles_tracked']} 辆车，视频时长 {result['duration']:.1f} 秒",
                "data": {
                    "vehicles_count": result["vehicles_tracked"],
                    "duration": round(result["duration"], 2),
                    "vehicles": vehicles_summary
                }
            }
        else:
            return {"status": "error", "message": result.get("error", "追踪失败")}
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"status": "error", "message": f"追踪出错: {str(e)}"}