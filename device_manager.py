# device_manager.py

import asyncio
import ctypes
import logging
import os
import re
import subprocess
import sys
import time

from pymobiledevice3.exceptions import NoDeviceConnectedError
from pymobiledevice3.lockdown import create_using_usbmux
from pymobiledevice3.remote.remote_service_discovery import (
    RemoteServiceDiscoveryService,
)
from pymobiledevice3.services.dvt.dvt_secure_socket_proxy import (
    DvtSecureSocketProxyService,
)

logger = logging.getLogger(__name__)


class DeviceManager:
    def __init__(self):
        self.device = None
        self.tunnel_process = None
        self.dvt_service = None
        self.tunnel_address = None
        self.tunnel_port = None

    def ensure_admin_rights(self):
        try:
            is_admin = os.getuid() == 0
        except AttributeError:
            is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
        if not is_admin:
            logger.error("请以管理员或root权限运行此脚本！")
            sys.exit(1)

    def get_device(self):
        while True:
            try:
                device = create_using_usbmux()
                if device.paired and not device.all_values.get("PasswordProtected"):
                    name = device.get_value(domain=None, key="DeviceName")
                    version = device.get_value(domain=None, key="ProductVersion")
                    logger.info(f"设备已连接: {name} (iOS {version})")
                    self.device = device
                    return
                else:
                    input("请解锁你的iPhone，并信任此电脑，然后按回车键...")
            except NoDeviceConnectedError:
                input("未检测到任何设备。请连接你的iPhone后按回车键...")
            time.sleep(1)

    def start_tunnel(self) -> bool:
        logger.info("正在启动隧道...")
        command = [sys.executable, "-m", "pymobiledevice3", "lockdown", "start-tunnel"]
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="ignore",
        )
        rsd_pattern = re.compile(r"--rsd\s+([\w:.-]+)\s+(\d+)")
        output_lines, timeout, start_time = [], 15, time.time()

        while time.time() - start_time < timeout:
            line = process.stdout.readline()
            if not line and process.poll() is not None:
                break
            if line:
                line_stripped = line.strip()
                output_lines.append(line_stripped)
                match = rsd_pattern.search(line_stripped)
                if match:
                    address, port = match.group(1), int(match.group(2))
                    logger.info(f"隧道已建立! RSD Address: {address}, Port: {port}")
                    self.tunnel_process, self.tunnel_address, self.tunnel_port = (
                        process,
                        address,
                        port,
                    )
                    return True

        logger.error("启动隧道失败或超时。未能从输出中找到RSD信息。")
        logger.error(
            "!!! 以下是来自 pymobiledevice3 lockdown start-tunnel 的原始输出: !!!"
        )
        for line in output_lines or ["(没有捕获到任何输出)"]:
            logger.error(f"  -> {line}")
        self.tunnel_address, self.tunnel_port = None, None
        process.kill()
        return False

    async def ensure_connection(self) -> bool:
        logging.getLogger("pymobiledevice3").setLevel(logging.DEBUG)
        if self.tunnel_process is None or self.tunnel_process.poll() is not None:
            logger.warning("隧道进程已断开或未启动。正在重建...")
            if self.tunnel_process:
                self.tunnel_process.kill()
            if not self.start_tunnel():
                return False
            logger.info("隧道已建立，等待2秒以确保服务稳定...")
            await asyncio.sleep(2)
            self.dvt_service = None

        if self.dvt_service is None:
            try:
                if not self.tunnel_address or not self.tunnel_port:
                    logger.error("隧道信息丢失，将强制重启隧道。")
                    if self.tunnel_process:
                        self.tunnel_process.kill()
                    self.tunnel_process = None
                    return False
                logger.info("正在连接DVT服务...")
                rsd = RemoteServiceDiscoveryService(
                    (self.tunnel_address, self.tunnel_port)
                )
                await asyncio.wait_for(rsd.connect(), timeout=15)
                dvt = DvtSecureSocketProxyService(rsd)
                dvt.perform_handshake()
                self.dvt_service = dvt
                logger.info("DVT服务连接成功！")
            except Exception as e:
                logging.getLogger("pymobiledevice3").setLevel(logging.WARNING)
                logger.error(f"连接DVT服务失败: {e}")
                return False

        logging.getLogger("pymobiledevice3").setLevel(logging.WARNING)
        return True

    def cleanup(self):
        if self.tunnel_process:
            logger.info("正在终止隧道进程...")
            self.tunnel_process.terminate()
            try:
                self.tunnel_process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.tunnel_process.kill()
