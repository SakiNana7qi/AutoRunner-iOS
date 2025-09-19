# path_utils.py

import ast
import logging
import math
import random
import sys
from geopy.distance import geodesic

logger = logging.getLogger(__name__)


def load_route_from_file(filepath: str) -> list:
    """从文件加载并解析路线"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
            path_data = ast.literal_eval(f"[{content}]")

        for point in path_data:
            point["lat"] = float(point["lat"])
            point["lng"] = float(point["lng"])

        logger.info(f"成功从 {filepath} 加载 {len(path_data)} 个基础路点。")
        return path_data
    except FileNotFoundError:
        logger.error(f"路线文件 {filepath} 未找到！")
        sys.exit(1)
    except Exception as e:
        logger.error(f"解析路线文件失败: {e}")
        sys.exit(1)


def bd09_to_wgs84(position: dict) -> dict:
    """百度坐标系 (BD-09) 转 WGS-84"""
    x_pi = 3.14159265358979324 * 3000.0 / 180.0
    pi = math.pi
    a = 6378245.0
    ee = 0.00669342162296594323

    def transform_lat(x, y):
        ret = (
            -100.0
            + 2.0 * x
            + 3.0 * y
            + 0.2 * y * y
            + 0.1 * x * y
            + 0.2 * math.sqrt(abs(x))
        )
        ret += (
            (20.0 * math.sin(6.0 * x * pi) + 20.0 * math.sin(2.0 * x * pi)) * 2.0 / 3.0
        )
        ret += (20.0 * math.sin(y * pi) + 40.0 * math.sin(y / 3.0 * pi)) * 2.0 / 3.0
        ret += (
            (160.0 * math.sin(y / 12.0 * pi) + 320 * math.sin(y * pi / 30.0))
            * 2.0
            / 3.0
        )
        return ret

    def transform_lon(x, y):
        ret = 300.0 + x + 2.0 * y + 0.1 * x * x + 0.1 * x * y + 0.1 * math.sqrt(abs(x))
        ret += (
            (20.0 * math.sin(6.0 * x * pi) + 20.0 * math.sin(2.0 * x * pi)) * 2.0 / 3.0
        )
        ret += (20.0 * math.sin(x * pi) + 40.0 * math.sin(x / 3.0 * pi)) * 2.0 / 3.0
        ret += (
            (150.0 * math.sin(x / 12.0 * pi) + 300.0 * math.sin(x / 30.0 * pi))
            * 2.0
            / 3.0
        )
        return ret

    lng, lat = position["lng"], position["lat"]
    x = lng - 0.0065
    y = lat - 0.006
    z = math.sqrt(x * x + y * y) - 0.00002 * math.sin(y * x_pi)
    theta = math.atan2(y, x) - 0.000003 * math.cos(x * x_pi)
    gcj_lng = z * math.cos(theta)
    gcj_lat = z * math.sin(theta)
    d_lat = transform_lat(gcj_lng - 105.0, gcj_lat - 35.0)
    d_lng = transform_lon(gcj_lng - 105.0, gcj_lat - 35.0)
    rad_lat = gcj_lat / 180.0 * pi
    magic = math.sin(rad_lat)
    magic = 1 - ee * magic * magic
    sqrt_magic = math.sqrt(magic)
    d_lat = (d_lat * 180.0) / ((a * (1 - ee)) / (magic * sqrt_magic) * pi)
    d_lng = (d_lng * 180.0) / (a / sqrt_magic * math.cos(rad_lat) * pi)
    return {"lat": gcj_lat * 2 - gcj_lat - d_lat, "lng": gcj_lng * 2 - gcj_lng - d_lng}


def interpolate_path(loc: list, v: float, dt: float) -> list:
    """对路径进行插值，以匹配速度和更新间隔"""
    if len(loc) < 2:
        return loc
    fixedLoc = []
    path_to_process = loc + [loc[0]]
    for i in range(len(path_to_process) - 1):
        p1, p2 = path_to_process[i], path_to_process[i + 1]
        dist = geodesic((p1["lat"], p1["lng"]), (p2["lat"], p2["lng"])).m
        if v <= 0:
            continue
        duration = dist / v
        steps = max(1, int(duration / dt))
        for step in range(steps):
            ratio = step / steps
            lat = p1["lat"] + (p2["lat"] - p1["lat"]) * ratio
            lng = p1["lng"] + (p2["lng"] - p1["lng"]) * ratio
            fixedLoc.append({"lat": lat, "lng": lng})
    return fixedLoc


def add_random_jitter(loc: list, d: float = 0.000025, n: int = 5) -> list:
    """为路径增加随机抖动"""
    if not loc:
        return []
    result = [p.copy() for p in loc]
    num_points = len(result)
    for i in range(n):
        start, end = int(i * num_points / n), int((i + 1) * num_points / n)
        offset_lat = (random.random() * 2 - 1) * d
        offset_lng = (random.random() * 2 - 1) * d
        for j in range(start, end):
            progress = (j - start) / (end - start) if (end - start) > 0 else 0
            smoothing_factor = math.sin(progress * math.pi)
            result[j]["lat"] += offset_lat * smoothing_factor
            result[j]["lng"] += offset_lng * smoothing_factor
    return result


def generate_lap_path(
    base_route: list, speed: float, speed_variation: float, update_interval: float
) -> list:
    """生成一整圈的详细、随机化的路径点"""
    v_rand = (
        1000 / (1000 / speed - (2 * random.random() - 1) * speed_variation)
        if speed > 0
        else 0
    )
    interpolated = interpolate_path(base_route, v_rand, update_interval)
    randomized = add_random_jitter(interpolated)
    logger.info(f"已生成新一圈的随机路线，共 {len(randomized)} 个坐标点。")
    return randomized
