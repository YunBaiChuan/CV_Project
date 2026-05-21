# agent/predictor.py
from collections import deque
import math

class PointSmoother:
    def __init__(self, alpha=0.5):
        self.alpha = alpha
        self.smoothed = None
    def update(self, x, y):
        if self.smoothed is None:
            self.smoothed = (float(x), float(y))
        else:
            sx, sy = self.smoothed
            sx = self.alpha * x + (1 - self.alpha) * sx
            sy = self.alpha * y + (1 - self.alpha) * sy
            self.smoothed = (sx, sy)
        return self.smoothed

class VelocitySmoother:
    def __init__(self, alpha=0.4):
        self.alpha = alpha
        self.vx_smoothed = None
        self.vy_smoothed = None
    def update(self, vx, vy):
        if self.vx_smoothed is None:
            self.vx_smoothed = float(vx)
            self.vy_smoothed = float(vy)
        else:
            self.vx_smoothed = self.alpha * vx + (1 - self.alpha) * self.vx_smoothed
            self.vy_smoothed = self.alpha * vy + (1 - self.alpha) * self.vy_smoothed
        return self.vx_smoothed, self.vy_smoothed

def estimate_distance(box_width_px, img_width_px, real_car_width=1.8, hfov=60):
    if box_width_px <= 0:
        return None
    focal = (img_width_px / 2) / math.tan(math.radians(hfov / 2))
    return (real_car_width * focal) / box_width_px


class TrajectoryPredictor:
    """轨迹预测器 - 基于速度平滑的线性外推"""
    
    def __init__(self, trail_len=30, predict_steps=10, smooth_alpha=0.5, velocity_alpha=0.4):
        self.trail_len = trail_len
        self.predict_steps = predict_steps
        self.smooth_alpha = smooth_alpha
        self.velocity_alpha = velocity_alpha
        
        # 存储轨迹数据
        self.trails = {}           # {track_id: deque of points}
        self.point_smoothers = {}  # {track_id: PointSmoother}
        self.velocity_smoothers = {} # {track_id: VelocitySmoother}
        self.last_positions = {}    # {track_id: last position}
    
    def update(self, track_id, x, y):
        """更新车辆轨迹，返回预测位置和速度"""
        # 轨迹平滑
        if track_id not in self.point_smoothers:
            self.point_smoothers[track_id] = PointSmoother(self.smooth_alpha)
        smooth_x, smooth_y = self.point_smoothers[track_id].update(x, y)
        
        # 记录历史轨迹
        if track_id not in self.trails:
            self.trails[track_id] = deque(maxlen=self.trail_len)
        self.trails[track_id].append((smooth_x, smooth_y))
        self.last_positions[track_id] = (smooth_x, smooth_y)
        
        # 计算速度并预测
        predicted_positions = []
        velocity = (0, 0)
        speed = 0
        
        if len(self.trails[track_id]) >= 2:
            prev = self.trails[track_id][-2]
            curr = self.trails[track_id][-1]
            vx = curr[0] - prev[0]
            vy = curr[1] - prev[1]
            
            # 速度平滑
            if track_id not in self.velocity_smoothers:
                self.velocity_smoothers[track_id] = VelocitySmoother(self.velocity_alpha)
            sm_vx, sm_vy = self.velocity_smoothers[track_id].update(vx, vy)
            velocity = (sm_vx, sm_vy)
            speed = math.sqrt(sm_vx**2 + sm_vy**2)
            
            # 预测未来位置
            last_x, last_y = curr
            for _ in range(self.predict_steps):
                last_x += sm_vx
                last_y += sm_vy
                predicted_positions.append((int(last_x), int(last_y)))
        
        return {
            "track_id": track_id,
            "smooth_position": (smooth_x, smooth_y),
            "velocity": velocity,
            "speed": speed,
            "predicted_positions": predicted_positions,
            "trail_length": len(self.trails[track_id])
        }
    
    def get_collision_risk(self, track_id, other_vehicles, min_distance=50):
        """评估碰撞风险"""
        if track_id not in self.last_positions:
            return None
        
        curr_x, curr_y = self.last_positions[track_id]
        
        risks = []
        for other_id, other_data in other_vehicles.items():
            if other_id == track_id:
                continue
            
            other_x, other_y = other_data.get("position", (0, 0))
            other_pred = other_data.get("predicted_positions", [])
            
            # 当前距离
            curr_dist = math.sqrt((curr_x - other_x)**2 + (curr_y - other_y)**2)
            
            # 预测距离（如果对方有预测位置）
            pred_dist = curr_dist
            if other_pred:
                pred_x, pred_y = other_pred[0]
                pred_dist = math.sqrt((curr_x - pred_x)**2 + (curr_y - pred_y)**2)
            
            if pred_dist < min_distance:
                risks.append({
                    "other_id": other_id,
                    "current_distance": round(curr_dist, 1),
                    "predicted_distance": round(pred_dist, 1),
                    "risk_level": "high" if pred_dist < 30 else "medium"
                })
        
        return risks
    
    def cleanup(self, active_ids):
        """清理不在活跃列表中的车辆数据"""
        for tid in list(self.trails.keys()):
            if tid not in active_ids:
                del self.trails[tid]
                if tid in self.point_smoothers:
                    del self.point_smoothers[tid]
                if tid in self.velocity_smoothers:
                    del self.velocity_smoothers[tid]
                if tid in self.last_positions:
                    del self.last_positions[tid]
    
    def get_trajectory(self, track_id):
        """获取车辆的完整轨迹"""
        if track_id not in self.trails:
            return []
        return list(self.trails[track_id])