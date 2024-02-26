from aiohttp import web, ClientSession
from functools import partial
import aiofiles
import argparse
import asyncio
import logging
import os
import signal


def signal_handler():    
    logging.debug(f'Received SIGINT, exiting...')    
    loop.stop()
    raise KeyboardInterrupt


async def archive(request, path='test_photos', delay=0):
    chunk_size = 1*1024  # 1KB
    archive_hash = request.match_info.get('archive_hash')
    command = ['zip', '-r', '-', '.']
    cwd = os.path.join(path, archive_hash)

    if not os.path.exists(cwd):
        logging.debug('Archive dont exist')
        return web.HTTPNotFound(text='Архив Удален')

    logging.debug('creating zip process..')
    proc = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=cwd)    

    response = web.StreamResponse()
    response.headers['Content-Type'] = 'text/html'
    response.headers['Content-Disposition'] = 'attachment; filename="archive.zip"'
    logging.debug('Sending HTTP headers')
    await response.prepare(request)

    try:
        async with ClientSession() as session:
            while True:
                logging.debug('Sending archive chunk ...')
                part = await proc.stdout.read(chunk_size)
                if delay:
                    await asyncio.sleep(delay)
                if not part:
                    logging.debug('EOF')
                    break
                await response.write(part)
    except asyncio.exceptions.CancelledError as e:
        logging.debug('Download was interrupted')
        proc.kill()
    except ConnectionResetError:
        logging.debug('Download was interrupted')
        proc.kill()
    except SystemExit:
        logging.debug('SystemExit exception')
        proc.kill()
    except LookupError:
        logging.debug('LookupError exception')
        proc.kill()

    return response


async def handle_index_page(request):
    async with aiofiles.open('index.html', mode='r') as index_file:
        index_contents = await index_file.read()
    return web.Response(text=index_contents, content_type='text/html')


def create_parser():
    parser = argparse.ArgumentParser(description='async download server')
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable Debug')
    parser.add_argument('-d', '--delay', default=0, type=int, help='set delay')
    parser.add_argument('-f', '--folder', default='test_photos', type=str, help='path to image folder')
    parser.add_argument('-i', '--ip', default='127.0.0.1', type=str, help='server IP')
    parser.add_argument('-p', '--port', default=8080, type=int, help='server port IP')
    return parser


if __name__ == '__main__':
    parser = create_parser()
    args = parser.parse_args()
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    loop = asyncio.get_event_loop()
    loop.add_signal_handler(signal.SIGINT, signal_handler)    
    app = web.Application()
    app.add_routes([
        web.get('/', handle_index_page),
        web.get('/archive/{archive_hash}/', partial(archive, delay=args.delay, path=args.folder)),
    ]) 
    
    runner = web.AppRunner(app)
    loop.run_until_complete(runner.setup())
    
    site = web.TCPSite(runner, args.ip, args.port)
    loop.run_until_complete(site.start())
    loop.run_forever()    
   