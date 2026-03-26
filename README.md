# 365Cam Stream

**Stream your cheap WiFi camera directly to your computer — no app, no cloud, no account needed.**

Bought a small WiFi camera from AliExpress / Amazon / Temu and it only works through a phone app? This tool lets you view the camera feed directly in your browser over your local network. Your video never leaves your home.

Works with cameras that use these apps:
**365Cam** | **IPC365** | **iMiniCam** | **iMiniCam Pro** | **WiFi Camera** | **Mini Camera** | **A9 Camera** | **Outdoor Camera** | **Spy Camera Viewer** | **P2P Camera** | **YCC365** | **CloudEdge** | and similar cheap Chinese WiFi cameras

> If your camera's app asks you to create an account on a Chinese cloud service and you wish you could just view it locally — this is for you.

## How It Works

These cameras use a protocol called PPPP to communicate. The phone apps normally send your video through servers in China, but the cameras also support direct local connections. This tool talks directly to your camera over your WiFi — nothing goes to the internet.

This tool:
1. Discovers the camera on your local network via UDP broadcast
2. Authenticates using the PPPP protocol (XOR1 encrypted)
3. Requests a video stream (JPEG frames)
4. Serves it as MJPEG over HTTP on a local web server

## Supported Cameras

Cameras with device IDs starting with these prefixes are likely compatible:

| Prefix | Protocol | Status |
|--------|----------|--------|
| DGOH | JSON | Tested, working |
| DGOK | JSON | Supported by aiopppp |
| PTZA | Binary | Supported by aiopppp |
| FTYC | Binary | Partial |

Your camera likely works if:
- The app uses a device ID like `DGOH...`, `DGOK...`, etc.
- The app connects to P2P relay servers on port 32100
- The camera responds to UDP discovery on port 32108

## Quick Start

**1. Clone and install:**

```bash
git clone https://github.com/YOUR_USERNAME/365cam-stream.git
cd 365cam-stream
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**2. Configure:**

```bash
cp .env.example .env
```

Open `.env` in any text editor and set your camera's IP:

```
CAMERA_IP=192.168.0.100    # Replace with your camera's IP address
PPPP_USER=admin             # Usually "admin" — don't change unless needed
PPPP_PASS=6666              # Usually "6666" — don't change unless needed
WEB_PORT=4000               # Port for the local web viewer
```

> **Don't know the camera IP?** Set `CAMERA_IP=255.255.255.255` to auto-discover all cameras on your network. Or check your router's connected devices list.

**3. Run:**

```bash
python stream.py
```

**4. Open your browser:**

Go to **http://localhost:4000** — you should see your camera's live feed.

**5. Stop:**

Press `Ctrl+C` in the terminal.

**6. Run again later:**

```bash
cd 365cam-stream
source venv/bin/activate
python stream.py
```

---

## Credentials

The camera password for streaming is **different** from the app login password.

| What | Username | Password |
|------|----------|----------|
| App / Cloud (e.g. 365Cam) | admin | admin123 |
| **This tool (streaming)** | **admin** | **6666** |

Most cameras use `admin` / `6666` by default. If it doesn't work, see [PROTOCOL.md](PROTOCOL.md) for how to find the right credentials.

## Tested On

This tool was developed and tested with a small WiFi camera (outdoor/spy type) using:
- **App**: 365Cam (Android)
- **Device ID prefix**: DGOH
- **Firmware**: HQLS_HQ6_20230908
- **Protocol**: JSON-based PPPP with XOR1 encryption

If your camera uses a similar app and protocol, it should work.

## Note on Controls

The web page has buttons like Fullscreen, Start/Stop Video, Resolution, and Reboot. Not all buttons work with every camera - it depends on what the camera firmware supports. Video streaming works on all tested cameras, but features like PTZ (pan/tilt), IR, and light control may do nothing or disconnect the session. This is normal.

## Troubleshooting

**No device found**
- Camera is off, on a different network, or IP is wrong
- Try `CAMERA_IP=255.255.255.255` for broadcast discovery
- Verify the camera is reachable: `ping <camera-ip>`

**Auth failed (result: -3)**
- Wrong PPPP password. Try `6666`, empty string, or `888888`
- The app login password (e.g. `admin123`) does NOT work for PPPP

**Video not showing**
- Click "Start Video" on the web page
- Reload the page
- Set `LOG_LEVEL=DEBUG` in `.env` to see detailed protocol logs

**Camera disconnects after a command**
- Some cameras don't support all features (IR, light, PTZ)
- Unsupported commands may crash the session — the tool auto-reconnects

## How It Was Reverse Engineered

See [PROTOCOL.md](PROTOCOL.md) for the full reverse engineering write-up, including:
- Protocol identification via packet capture
- XOR1 encryption analysis
- JPEG frame extraction from encrypted UDP packets
- P2P discovery and handshake sequences

## Credits

- [aiopppp](https://github.com/devbis/aiopppp) — Python PPPP protocol library
- [PCAPdroid](https://github.com/emanuele-f/PCAPdroid) — Android packet capture without root

## License

MIT

---

<sub>**Keywords**: 365cam stream local, ipc365 without app, mini wifi camera stream pc, cheap chinese camera local stream, p2p camera without cloud, aliexpress camera stream computer, spy camera viewer alternative, a9 camera stream, wifi camera no app needed, PPPP protocol camera, iminicam stream, ycc365 local, cloudedge alternative, mini camera stream browser, wifi camera direct connection, chinese ip camera hack stream, p2p ip camera local network</sub>
