# config.py

# --- 全局配置 ---
CONFIG = {
    "ROUTE_FILE": "ZZGWest.txt",  # 路径文件名
    "SPEED_MPS": 3.3,  # 平均速度 (米/秒)
    "SPEED_VARIATION": 15,  # 速度随机变化范围 (值越大，速度波动越大)
    "UPDATE_INTERVAL_SEC": 0.5,  # GPS坐标更新的间隔时间 (秒)
    "RECONNECT_DELAY_SEC": 5,  # 连接失败后的重试延迟 (秒)
}
