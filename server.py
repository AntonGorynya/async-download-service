from aiohttp import web, ClientSession
import aiofiles
import asyncio
import os


INTERVAL_SECS = 1


async def archive(request):
    chunk_size = 100
    archive_hash = request.match_info.get('archive_hash')
    command = ['zip','-r', '-', '.']
    cwd = os.path.join('test_photos', archive_hash)

    if os.path.exists(cwd):
        proc = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd)


        response = web.StreamResponse()
        response.headers['Content-Type'] = 'text/html'
        response.headers['Content-Disposition'] = 'attachment; filename="archive.zip"'
        # Отправляет клиенту HTTP заголовки
        await response.prepare(request)


        async with ClientSession() as session:
            while True:
                part = await proc.stdout.read(chunk_size)
                if not part:
                    break
                await response.write(part)
        return response
    return web.HTTPNotFound(text='Архив Удален')


async def handle_index_page(request):
    async with aiofiles.open('index.html', mode='r') as index_file:
        index_contents = await index_file.read()
    return web.Response(text=index_contents, content_type='text/html')


if __name__ == '__main__':
    app = web.Application()
    app.add_routes([
        web.get('/', handle_index_page),
        web.get('/archive/{archive_hash}/', archive),
    ])
    web.run_app(app)
