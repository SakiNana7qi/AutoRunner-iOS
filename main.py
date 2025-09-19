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

    simulator = GPSSimulator(CONFIG)
    try:
        asyncio.run(simulator.run())
    except KeyboardInterrupt:
        simulator.cleanup()
        logger.info("程序已由用户中断。")


if __name__ == "__main__":
    main()
