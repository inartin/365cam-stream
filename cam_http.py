"""
Custom web UI for 365cam-stream: same routes as aiopppp.http_server but with a fullscreen control.
"""

import asyncio
import logging

from aiohttp import web

from aiopppp.http_server import SESSIONS, handle_commands, stream_video

logger = logging.getLogger(__name__)


async def index(request):
    js = '''
    <script>
    function sendCommand(dev_id, cmd, params) {
        var par = new URLSearchParams(params).toString()
        fetch(`/${dev_id}/c/${cmd}`, {
            method: 'POST',
            body: JSON.stringify(params),
        });
        return false;
    }
    function fullscreenFeed(img) {
        if (!img) return;
        if (document.fullscreenElement === img) {
            document.exitFullscreen();
            return;
        }
        if (img.requestFullscreen) {
            img.requestFullscreen();
        } else if (img.webkitRequestFullscreen) {
            img.webkitRequestFullscreen();
        }
    }
    </script>
    '''
    videos = '<hr/>'.join(
        f'<h2>{x}</h2>'
        f'<div class="cam-feed"><img src="/{x}/v" alt="Live feed {x}"/>'
        f'<button type="button" onclick="fullscreenFeed(this.parentElement.querySelector(\'img\'))">Fullscreen</button></div>'
        f'<br/>'
        f'<button onClick="sendCommand(\'{x}\', \'toggle-lamp\', {{value: 1}})">Light ON</button>'
        f'<button onClick="sendCommand(\'{x}\', \'toggle-lamp\', {{value: 0}})">Light OFF</button>'
        f'<button onClick="sendCommand(\'{x}\', \'toggle-ir\', {{value: 1}})">IR ON</button>'
        f'<button onClick="sendCommand(\'{x}\', \'toggle-ir\', {{value: 0}})">IR OFF</button>'
        '<br>'
        f'<button onClick="sendCommand(\'{x}\', \'rotate\', {{value: \'LEFT\'}})">LEFT</button>'
        f'<button onClick="sendCommand(\'{x}\', \'rotate\', {{value: \'RIGHT\'}})">RIGHT</button>'
        f'<button onClick="sendCommand(\'{x}\', \'rotate\', {{value: \'UP\'}})">UP</button>'
        f'<button onClick="sendCommand(\'{x}\', \'rotate\', {{value: \'DOWN\'}})">DOWN</button>'
        f'<button onClick="sendCommand(\'{x}\', \'rotate-stop\', {{}})">Rotate STOP</button>'
        '<br>'
        f'<button onClick="sendCommand(\'{x}\', \'start-video\', {{}})">Start Video</button>'
        f'<button onClick="sendCommand(\'{x}\', \'stop-video\', {{}})">Stop Video</button>'
        ' Resolution: '
        f'<select onChange="sendCommand(\'{x}\', \'set-video-param\', {{name: \'resolution\', value: this.value}})">'
            '<option>QVGA</option>'
            '<option>VGA</option>'
            '<option>HD</option>'
            '<option>FD</option>'
            '<option>UD</option>'
        '</select>'
        ' Rotate: '
        f'<select onChange="sendCommand(\'{x}\', \'set-video-param\', {{name: \'rotate\', value: this.value}})">'
            '<option>NORMAL</option>'
            '<option>H</option>'
            '<option>V</option>'
            '<option>HV</option>'
        '</select>'
        ' Bitrate: '
        f'<input type="range" min="0" max="100" onChange="sendCommand(\'{x}\', \'set-video-param\', {{name: \'bitrate\', value: +this.value}})")>'
        '<br>'
        f'<button onClick="sendCommand(\'{x}\', \'reboot\', {{}})">Reboot</button>'
        for x in SESSIONS.keys())
    style = '''
    <style>
    .cam-feed img { max-width: 100%; height: auto; vertical-align: middle; }
    .cam-feed button { margin-left: 0.5rem; }
    .cam-feed img:fullscreen { object-fit: contain; width: 100%; height: 100%; background: #000; }
    </style>
    '''
    return web.Response(
        text="<!doctype html><html><head><meta charset=\"utf-8\"><title>PPPP Cameras</title>{}</head><body>{}<h1>PPPP Cameras</h1>{}</body></html>".format(
            style,
            js,
            videos,
        ),
        headers={'content-type': 'text/html; charset=utf-8'},
    )


async def start_web_server(port=4000):
    app = web.Application()
    app.router.add_get('/', index)
    app.router.add_get('/{dev_id}/v', stream_video)
    app.router.add_post('/{dev_id}/c/{cmd}', handle_commands)

    runner = web.AppRunner(app, handle_signals=True)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    try:
        logger.info(f'Starting web server on port {port}')
        await site.start()
        try:
            await asyncio.Future()
        except asyncio.CancelledError:
            pass
    finally:
        logger.info('Shutting down web server')
        await runner.cleanup()
