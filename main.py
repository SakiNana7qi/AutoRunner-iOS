# main.py

import asyncio
import logging
import coloredlogs
from simulator import GPSSimulator
from config import CONFIG


def main():
    # 初始化日志
    coloredlogs.install(level="INFO", fmt="%(asctime)s - %(levelname)s - %(message)s")
    logging.getLogger("pymobiledevice3").setLevel(logging.WARNING)
    logger = logging.getLogger(__name__)

    import argparse

    parser = argparse.ArgumentParser(description="Auto 冲冲步")
    parser.add_argument("--path", type=str, default="ZZGWest.txt", help="路径文件选择")
    parser.add_argument("--time", type=int, default=1000, help="时间（s）")
    parser.add_argument("--speed", type=float, default=3.1, help="速度（m/s）")

    args = parser.parse_args()

    CONFIG["ROUTE_FILE"] = args.path
    CONFIG["SPEED_MPS"] = args.speed
    CONFIG["TOTALTIME"] = args.time

    simulator = GPSSimulator(CONFIG)
    try:
        asyncio.run(simulator.run())
    except KeyboardInterrupt:
        simulator.cleanup()
        logger.info("程序已由用户中断。")


if __name__ == "__main__":
    main()
