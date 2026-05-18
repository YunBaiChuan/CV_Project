USE driving_agent_db;

CREATE TABLE IF NOT EXISTS users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    email VARCHAR(100),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS alarm_records (
    id INT PRIMARY KEY AUTO_INCREMENT,
    alarm_type VARCHAR(50) NOT NULL COMMENT '警告类型：speeding, collision_risk, lane_departure等',
    alarm_level INT DEFAULT 2 COMMENT '等级：1-紧急, 2-严重, 3-一般',
    info TEXT NOT NULL COMMENT '详细信息',
    vehicle_id VARCHAR(50) COMMENT '关联车辆ID',
    video_name VARCHAR(255) COMMENT '关联视频名称',
    user_id INT COMMENT '用户ID（关联users表）',
    trigger_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '触发时间',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_trigger_time ON alarm_records(trigger_time);
CREATE INDEX idx_user_id ON alarm_records(user_id);
CREATE INDEX idx_alarm_type ON alarm_records(alarm_type);