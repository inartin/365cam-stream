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
import aiopppp.discover
from aiopppp.http_server import SESSIONS

from cam_http import start_web_server
from aiopppp.session import make_session

async def custom_create_udp_server(port, on_receive):
    bind_ip = '0.0.0.0'
    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        bind_ip = s.getsockname()[0]
        s.close()
    except Exception:
        pass

    loop = asyncio.get_running_loop()
    transport, _ = await loop.create_datagram_endpoint(
        lambda: aiopppp.discover.DiscoverUDPProtocol(on_receive),
        local_addr=(bind_ip, port),
        allow_broadcast=True,
    )
    return transport

aiopppp.discover.create_udp_server = custom_create_udp_server

logger = logging.getLogger(__name__)

discovery = None
tasks = {}
new_device_fut = None


def get_new_device_fut():
    return new_device_fut


def on_device_found(device):
    if device.dev_id.dev_id in SESSIONS:
        return
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


async def subnet_spray_discover(callback):
    from aiopppp.discover import Discovery, DiscoverUDPProtocol
    from aiopppp.const import PacketType
    from aiopppp.packets import parse_packet
    from aiopppp.types import DeviceDescriptor, Encryption

    logger = logging.getLogger("spray_discover")

    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except Exception:
        local_ip = "0.0.0.0"

    targets = ["255.255.255.255", "<broadcast>"]
    if local_ip != "0.0.0.0":
        prefix = local_ip.rsplit('.', 1)[0]
        targets.append(f"{prefix}.255")
        for i in range(1, 255):
            targets.append(f"{prefix}.{i}")

    packets = Discovery.get_possible_discovery_packets()
    d_decoder = Discovery()

    def on_receive(data, addr):
        try:
            encryption, decoded = d_decoder.maybe_decode(data)
        except ValueError:
            return
        pkt = parse_packet(decoded)
        if pkt.type == PacketType.PunchPkt:
            dev_id = pkt.as_object()
            logger.info(f"Found camera {dev_id} at {addr[0]}")
            device = DeviceDescriptor(
                dev_id=dev_id, addr=addr[0], port=addr[1],
                encryption=encryption, is_json=encryption != Encryption.NONE
            )
            callback(device)

    loop = asyncio.get_running_loop()
    transport, _ = await loop.create_datagram_endpoint(
        lambda: DiscoverUDPProtocol(on_receive),
        local_addr=(local_ip, 0),
        allow_broadcast=True
    )

    try:
        while True:
            for target_ip in targets:
                for p in packets:
                    try:
                        transport.sendto(p, (target_ip, 32108))
                    except Exception:
                        pass
            await asyncio.sleep(5)
    finally:
        transport.close()


async def amain():
    global new_device_fut
    
    discovery_tasks = []
    if CAMERA_IP in ("255.255.255.255", "<broadcast>"):
        discovery_tasks.append(asyncio.create_task(subnet_spray_discover(on_device_found)))
    else:
        d = Discovery(remote_addr=CAMERA_IP)
        discovery_tasks.append(asyncio.create_task(d.discover(on_device_found)))

    webserver_task = asyncio.create_task(start_web_server(port=WEB_PORT))
    try:
        while True:
            new_device_fut = asyncio.Future()
            dev_tasks = set(t for task_list in tasks.values() for t in task_list)
            wait_tasks = discovery_tasks + [webserver_task, new_device_fut] + list(dev_tasks)
            done, pending = await asyncio.wait(
                wait_tasks,
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
