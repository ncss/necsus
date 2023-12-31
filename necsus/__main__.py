import uvicorn

from .server import app

config = uvicorn.Config(
    app=app,
    host='localhost',
    port=6277,

    # We are running an async framework, with uvloop as the backing event loop.
    # As a result, we need only one process and one thread.
    loop='uvloop',
    workers=1,

    # When running behind a reverse proxy, connections will always seem to come from localhost, and this makes the
    # access logs less useful than they could be. These reverse proxies add some extra X-Forwarded-For headers of where
    # the request actually came from, and setting the forwarded_allow_ips option makes uvicorn trust this information.
    forwarded_allow_ips='*',
    log_config='logconfig.yaml',
)

if __name__ == '__main__':
    server = uvicorn.Server(config)
    server.run()
