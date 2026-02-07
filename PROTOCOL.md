# PPPP Camera Protocol — Reverse Engineering Report

How the 365Cam / PPPP camera protocol was reverse engineered and how the video stream was extracted.

---

## Target

| Property | Value |
|----------|-------|
| App | 365Cam (Android) |
| Protocol | PPPP / CS2 Network P2P |
| Encryption | XOR1 |
| Video format | JPEG frames over UDP |

---

## Step 1: HTTP API Capture

The 365Cam app uses a cloud API for auth and device registration. Captured via **mitmproxy** with the Android phone proxied through a Mac.

- `POST /push/login` — app credentials, returns auth token
- `POST /push/regAdd/app` — registers the app with the device ID
- `POST /push/dev/add` — links the device to the account

These HTTP API credentials are **not** used for the video stream.

---

## Step 2: Dead Ends

- **RTSP** — port 554 refused, not available
- **All TCP ports filtered** — nmap showed every port closed/filtered
- **Can't sniff WiFi traffic from Mac** — tshark on Mac only sees traffic to/from the Mac itself, not between phone and camera on the same WiFi network

---

## Step 3: Phone-Side Packet Capture

Breakthrough: captured traffic **on the Android phone** using [PCAPdroid](https://github.com/emanuele-f/PCAPdroid) (no root needed).

This revealed the full protocol:

### P2P Discovery (port 32100)

The phone sends 4-byte UDP probes to P2P relay servers. These servers return routing info so the phone can find the camera on the LAN.

```
Phone → 3.10.99.101:32100    (4 bytes: probe)
Phone → 139.9.86.167:32100   (4 bytes: probe)
Phone → 3.227.45.161:32100   (4 bytes: probe)
       ← 20 bytes: routing response
```

### Direct LAN Connection

After discovery, the phone connects directly to the camera via UDP:

1. Phone sprays 19-byte hello packets to camera ports 17700-17706 (hole-punching)
2. Camera responds on one port
3. 182-byte authentication exchange
4. Video data starts flowing

### Traffic Breakdown

| Direction | Volume | Content |
|-----------|--------|---------|
| Camera → Phone | 1,586 KB | Video (1,463 packets of 1,027 bytes) |
| Phone → Camera | 20 KB | Commands and keepalives |

Duration: 16.8 seconds, 2,049 total packets.

---

## Step 4: Protocol Identification

Identified as **PPPP / CS2 Network P2P** (Shenzhen Yunni Technology):

- Port 32100 for P2P server discovery
- Device ID prefix `DGOH`
- 4-character device key
- Multi-port UDP hole-punching
- XOR1 encryption on all packets

---

## Step 5: Decryption

Applied XOR1 decryption (from the `aiopppp` library) to the captured video packets:

```
Encrypted: 2788 63ee 3fde 835a da60 51fd 7643...
Decoded:   fa00 0055 aa15 a803 03e4 02cf 0200...
                 ^^^^^^^^^^^
                 Video frame marker (55 aa 15 a8)
```

32 bytes after the marker: `ff d8 ff db 00 84...` — a **JPEG Start of Image (SOI)**.

The video is standard JPEG frames wrapped in PPPP Drw (data relay) packets, XOR1 encrypted.

---

## Step 6: LAN Discovery

The camera responds to LAN discovery broadcasts on port 32108 — no cloud servers needed:

```
Mac → 192.168.0.x:32108   (broadcast: LanSearch)
     ← Camera responds with PunchPkt containing device ID and port
```

---

## Step 7: Credentials

The PPPP protocol uses **different credentials** than the HTTP cloud API:

| Context | Username | Password |
|---------|----------|----------|
| HTTP API (cloud) | admin | (app-specific) |
| **PPPP (video)** | **admin** | **6666** |

Found by XOR1-decoding the authentication packet from the pcap:

```json
{"pro": "check_user", "cmd": 100, "user": "admin", "pwd": "6666"}
```

---

## Protocol Flow

```
┌─────────┐                              ┌────────┐
│ Client  │                              │ Camera │
└────┬────┘                              └───┬────┘
     │                                       │
     │── LanSearch (UDP broadcast:32108) ───>│
     │<── PunchPkt (device ID + port) ──────│
     │                                       │
     │── PunchPkt (XOR1 encrypted) ────────>│
     │<── P2pRdy ──────────────────────────│
     │                                       │
     │── check_user (admin/6666) ──────────>│
     │<── auth OK (result: 0) ─────────────│
     │── get_parms ────────────────────────>│
     │<── camera properties ───────────────│
     │                                       │
     │── CMD_STREAM (video=1) ─────────────>│
     │<══ JPEG frames (Drw packets) ═══════│
     │                                       │
     │── P2PAlive (keepalive) ─────────────>│
     │<── P2PAliveAck ─────────────────────│
```

All packets XOR1 encrypted. Video frames: `55 aa 15 a8` marker + 32-byte header + raw JPEG data.

---

## Packet Encryption

The XOR1 cipher is a substitution cipher using a 256-byte lookup table and a 4-byte key `(0x69, 0x97, 0xcc, 0x19)`. Each byte is XORed with a table value derived from the previous ciphertext byte. Decryption is byte-by-byte and stateful.

See [`aiopppp/encrypt.py`](https://github.com/devbis/aiopppp/blob/main/aiopppp/encrypt.py) for the full implementation.

---

## Tools Used

| Tool | Purpose |
|------|---------|
| mitmproxy | Captured HTTP API calls from Android phone |
| PCAPdroid | Captured all phone network traffic without root |
| tshark | Analyzed pcap files |
| nmap | Port scanning (all TCP ports filtered) |
| aiopppp | Python PPPP protocol library |

---

## Key Takeaways

1. HTTP API credentials are not the same as PPPP video credentials
2. Can't sniff phone-to-camera traffic from another device on WiFi — use PCAPdroid on the phone
3. All TCP ports are filtered — the camera only speaks UDP via the PPPP protocol
4. XOR1 encryption hides JPEG markers but is trivially reversible
5. No cloud needed for LAN streaming — direct UDP to the camera
