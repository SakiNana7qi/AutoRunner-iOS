# simulator.py

import asyncio
import logging
import sys

from pymobiledevice3.services.dvt.instruments.location_simulation import (
    LocationSimulation,
)

from device_manager import DeviceManager
import path_utils

logger = logging.getLogger(__name__)


class GPSSimulator:
    def __init__(self, config):
        self.config = config
        self.device_manager = DeviceManager()
        self.base_route = path_utils.load_route_from_file(config["ROUTE_FILE"])
        self.current_lap_path = []
        self.resume_index = 0

    async def run(self):
        self.device_manager.ensure_admin_rights()
        self.device_manager.get_device()

        while True:
            try:
                if not await self.device_manager.ensure_connection():
                    logger.warning(
                        f"{self.config['RECONNECT_DELAY_SEC']}秒后将重试连接..."
                    )
                    await asyncio.sleep(self.config["RECONNECT_DELAY_SEC"])
                    continue

                if self.resume_index >= len(self.current_lap_path):
                    print("-" * 50)
                    logger.info("当前圈已完成，正在规划下一圈...")
                    self.current_lap_path = path_utils.generate_lap_path(
                        self.base_route,
                        self.config["SPEED_MPS"],
                        self.config["SPEED_VARIATION"],
                        self.config["UPDATE_INTERVAL_SEC"],
                    )
                    self.resume_index = 0
                    print(
                        f"已开始模拟跑步，速度大约为 {self.config['SPEED_MPS']:.2f} m/s"
                    )

                point = self.current_lap_path[self.resume_index]
                wgs84_point = path_utils.bd09_to_wgs84(point)

                LocationSimulation(self.device_manager.dvt_service).set(
                    *wgs84_point.values()
                )

                progress = (self.resume_index + 1) / len(self.current_lap_path) * 100
                sys.stdout.write(
                    f"\r进度: {progress:3.1f}% | "
                    f"坐标点: {self.resume_index + 1}/{len(self.current_lap_path)} | "
                    f"Lat: {wgs84_point['lat']:.6f}, Lng: {wgs84_point['lng']:.6f}"
                )
                sys.stdout.flush()

                self.resume_index += 1
                await asyncio.sleep(self.config["UPDATE_INTERVAL_SEC"])

            except (
                ConnectionError,
                TimeoutError,
                BrokenPipeError,
                OSError,
                asyncio.TimeoutError,
            ) as e:
                logger.warning(f"\n发生连接错误: {type(e).__name__}。正在准备恢复...")
                self.device_manager.dvt_service = None
                if self.device_manager.tunnel_process:
                    self.device_manager.tunnel_process.kill()
                self.device_manager.tunnel_process = None
                logger.info(
                    f"{self.config['RECONNECT_DELAY_SEC']}秒后将从断点处自动恢复..."
                )
                await asyncio.sleep(self.config["RECONNECT_DELAY_SEC"])

            except KeyboardInterrupt:
                logger.info("\n接收到退出信号，正在清理...")
                break
            except Exception as e:
                logger.error(f"\n发生未知严重错误: {e}")
                break

        self.cleanup()

    def cleanup(self):
        self.device_manager.cleanup()
        print("\n再见！")
