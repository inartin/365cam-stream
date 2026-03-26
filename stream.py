#!/usr/bin/env python3
"""
365Cam PPPP Stream — Local video streaming for PPPP-based cameras.

Discovers the camera on the local network, authenticates via the PPPP protocol,
and serves a live MJPEG stream over HTTP.

Configuration is loaded from a .env file. See .env.example for details.
"""

import os
import sys
import asyncio
import logging

from dotenv import load_dotenv

load_dotenv()

CAMERA_IP = os.getenv("CAMERA_IP", "255.255.255.255")
PPPP_USER = os.getenv("PPPP_USER", "admin")
PPPP_PASS = os.getenv("PPPP_PASS", "6666")
WEB_PORT = int(os.getenv("WEB_PORT", "4000"))

from aiopppp.discover import Discovery
from aiopppp.http_server import SESSIONS

from cam_http import start_web_server
from aiopppp.session import make_session

logger = logging.getLogger(__name__)

discovery = None
tasks = {}
new_device_fut = None


def get_new_device_fut():
    return new_device_fut


def on_device_found(device):
    session = make_session(device, on_device_lost=on_device_lost, login=PPPP_USER, password=PPPP_PASS)
    SESSIONS[device.dev_id.dev_id] = session
    session.start()
    tasks[device.dev_id.dev_id] = session.running_tasks()
    get_new_device_fut().set_result(None)


def on_device_lost(device):
    logger.warning("Device %s lost", device.dev_id)
    SESSIONS.pop(device.dev_id.dev_id, None)
    tasks.pop(device.dev_id.dev_id, None)
    get_new_device_fut().set_result(None)


async def amain():
    global discovery, new_device_fut
    discovery = Discovery(remote_addr=CAMERA_IP)

    discovery_task = asyncio.create_task(discovery.discover(on_device_found))
    webserver_task = asyncio.create_task(start_web_server(port=WEB_PORT))
    try:
        while True:
            new_device_fut = asyncio.Future()
            dev_tasks = set(t for task_list in tasks.values() for t in task_list)
            done, pending = await asyncio.wait(
                [discovery_task, webserver_task, new_device_fut, *dev_tasks],
                return_when=asyncio.FIRST_COMPLETED,
            )
            if new_device_fut in pending:
                break
        if done:
            await asyncio.gather(*done)
    finally:
        for dev_id, session in list(SESSIONS.items()):
            session.stop()
        SESSIONS.clear()


def main():
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(level=logging.getLevelName(log_level))

    print(f"365Cam PPPP Stream")
    print(f"  Camera:  {CAMERA_IP}")
    print(f"  Auth:    {PPPP_USER} / {'*' * len(PPPP_PASS)}")
    print(f"  Web UI:  http://localhost:{WEB_PORT}")
    print()

    asyncio.run(amain())


if __name__ == "__main__":
    main()
