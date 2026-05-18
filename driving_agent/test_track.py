"""
测试实时车辆追踪（带可视化窗口）
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from agent.models.vehicle_tracker import VehicleTracker

def test_realtime():
    print("=" * 60)
    print("实时车辆追踪测试（带可视化窗口）")
    print("=" * 60)
    
    # 初始化追踪器（show_preview=True 显示实时画面）
    tracker = VehicleTracker(
        model_path="models/best.pt",
        show_preview=True  # 显示实时窗口
    )
    
    # 加载模型
    tracker.load_model()
    
    # 追踪视频
    test_video = "test_video.mp4"
    if os.path.exists(test_video):
        print(f"\n开始追踪: {test_video}")
        print("提示: 按 'Q' 键提前退出，或等待视频结束\n")
        
        result = tracker.track_video_realtime(test_video, save_output=True)
        
        print(f"\n✅ 追踪完成!")
        print(f"   - 视频时长: {result['duration']:.2f}秒")
        print(f"   - 追踪到 {result['vehicles_tracked']} 辆车")
        print(f"   - 输出视频: {test_video.replace('.mp4', '_tracked.mp4')}")
        
        # 显示车辆统计
        print(f"\n车辆统计:")
        for v in result['vehicles'][:5]:  # 只显示前5辆
            print(f"   - {v['vehicle_id']}: {v['trajectory_length']} 个轨迹点, 平均速度 {v['avg_speed']:.1f}")
    else:
        print(f"❌ 未找到测试视频: {test_video}")

if __name__ == "__main__":
    test_realtime()