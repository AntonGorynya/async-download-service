from aiohttp import web, ClientSession, ClientConnectionError
import aiofiles
import asyncio
import logging
import os


async def archive(request):
    chunk_size = 1*1024 # 1KB
    archive_hash = request.match_info.get('archive_hash')
    command = ['zip','-r', '-', '.']
    cwd = os.path.join('test_photos', archive_hash)

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
        async with ClientSession(timeout=1) as session:
            while True:
                logging.debug('Sending archive chunk ...')
                part = await proc.stdout.read(chunk_size)
                await asyncio.sleep(3)
                if not part:
                    logging.debug('EOF')
                    break
                await response.write(part)
    except asyncio.exceptions.CancelledError as e:
        logging.debug('Download was interrupted')
        proc.kill()

    return response


async def handle_index_page(request):
    async with aiofiles.open('index.html', mode='r') as index_file:
        index_contents = await index_file.read()
    return web.Response(text=index_contents, content_type='text/html')


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    app = web.Application()
    app.add_routes([
        web.get('/', handle_index_page),
        web.get('/archive/{archive_hash}/', archive),
    ])
    web.run_app(app)
