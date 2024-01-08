import asyncio
import contextlib
import json
import logging
import pathlib
import sqlite3

from starlette.applications import Starlette
from starlette.config import Config
from starlette.endpoints import HTTPEndpoint, WebSocketEndpoint
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse, RedirectResponse
from starlette.routing import Mount, Route, WebSocketRoute
from starlette.staticfiles import StaticFiles
from starlette.websockets import WebSocket

from . import (
    broker,
    db,
    events,
)

# Config will be read from environment variables (first priority), falling back to a .env file.
config = Config('.env', env_prefix='NECSUS_')

BASE_DIR = pathlib.Path(__file__).parent.parent

logger = logging.getLogger('necsus')


def create_db_connection(db_path: str) -> sqlite3.Connection:
    """Create and initialise a connection to an Sqlite3 database."""

    PRAGMAS = [
        'PRAGMA journal_mode = WAL',  # Use write-ahead log to allow concurrent readers during a write.
        'PRAGMA synchronous = normal',  # Default is 'full', which requires a full fsync after each commit.
    ]

    connection = sqlite3.connect(db_path)
    for sql in PRAGMAS:
        connection.execute(sql)

    with open(BASE_DIR / 'schema.sql') as f:
        connection.executescript(f.read())

    connection.commit()
    return connection


@contextlib.asynccontextmanager
async def lifespan(app: Starlette):
    # Read the environment variable NECSUS_DB, with a sensible default of the repo root.
    db_path = config.get('DB', str, str(BASE_DIR / 'necsus.db'))

    logger.info(f"Connecting to SQLite database {db_path!r}")
    connection = create_db_connection(db_path)

    app.state.connection = connection
    app.state.db = db.DB(connection)

    app.state.broker = broker.Broker()

    yield

    app.state.connection.close()


class Lobby(HTTPEndpoint):
    async def get(self, request):
        return FileResponse(BASE_DIR / 'client/lobby.html')


class Room(HTTPEndpoint):
    async def get(self, request):
        return FileResponse(BASE_DIR / 'client/index.html')


class Docs(HTTPEndpoint):
    async def get(self, request):
        return RedirectResponse('/docs/', status_code=301)


class ApiSpec(HTTPEndpoint):
    async def get(self, request):
        return FileResponse(BASE_DIR / 'api.yaml')


class ApiMessages(HTTPEndpoint):
    async def get(self, request):
        """
        List all messages in a room with IDs strictly larger than 'since'.
        If 'since' is not specified, list all messages in the room.
        """
        if (room := request.query_params.get('room')) is None:
            return JSONResponse({'message': 'The room name is required.'}, status_code=400)

        since_id = -1
        try:
            since_id = int(request.query_params.get('since', '-1'))
        except:
            pass

        new_messages = list(request.app.state.db.messages.since(room, since_id))
        return JSONResponse(new_messages)


class ApiBots(HTTPEndpoint):
    async def get(self, request: Request):
        """List all bots in a room, or if no room is given, list all bots on the server."""
        if (room := request.query_params.get('room')) is not None:
            bots = list(request.app.state.db.bots.find_all(room=room))
        else:
            bots = list(request.app.state.db.bots.find_all())

        return JSONResponse(bots)


class ApiActionsMessage(HTTPEndpoint):
    async def post(self, request: Request):
        """Post a message to a room."""
        try:
            data = await request.json()
        except json.JSONDecodeError:
            return JSONResponse({'message': 'Invalid JSON'}, status_code=400)

        text, room, author, image, media, css, js, base_url = [data.get(key) for key in ['text', 'room', 'author', 'image', 'media', 'css', 'js', 'base_url']]
        if None in (text, room, author):
            return JSONResponse({'message': f'All of text, room, and author should be non-null, got {text=}, {room=}, {author=}'}, status_code=400)

        message = await events.trigger_message_post(request.app.state.db, request.app.state.broker, room, author, text, image, media, css, js, base_url)
        return JSONResponse(message)


class ApiActionsMessageForm(HTTPEndpoint):
    async def post(self, request: Request):
        """A user in a room has submitted a form which was in a bot message. Pass the form data back to the bot."""
        try:
            data = await request.json()
        except json.JSONDecodeError:
            return JSONResponse({'message': 'Invalid JSON'}, status_code=400)

        room, author, bot_id, form_data, action_url = [data.get(key) for key in ['room', 'author', 'bot_id', 'form_data', 'action_url']]
        if None in (room, author, bot_id, form_data):
            return JSONResponse({'message': f'All of room, author, bot, form_data, and action_url should be non-null, got {room=}, {author=}, {bot_id=}, {form_data=}, {action_url=}'}, status_code=400)

        await events.trigger_message_form_post(request.app.state.db, request.app.state.broker, room, author, bot_id, action_url, form_data)
        return JSONResponse({})


class ApiActionBot(HTTPEndpoint):
    async def post(self, request: Request):
        """Create a bot, or update one with the specified ID."""
        try:
            data = await request.json()
        except json.JSONDecodeError:
            return JSONResponse({'message': 'Invalid JSON'}, status_code=400)

        id, room, name, responds_to, url = [data.get(key) for key in ['id', 'room', 'name', 'responds_to', 'url']]
        bot = request.app.state.db.bots.update_or_add(id=id, room=room, name=name, responds_to=responds_to, url=url)
        app.state.broker.put_bot(bot['room'], bot)
        return JSONResponse(bot)

    async def delete(self, request: Request):
        """Delete a bot with a specific ID."""
        try:
            data = await request.json()
        except json.JSONDecodeError:
            return JSONResponse({'message': 'Invalid JSON'}, status_code=400)

        if (id := data.get('id')) is None:
            return JSONResponse({'message': 'Need to provide the ID of the bot to remove.'}, status_code=400)

        if (bot := request.app.state.db.bots.find(id=id)) is None:
            return JSONResponse({'message': f'Bot with {id=} not found.'}, status_code=400)

        request.app.state.db.bots.remove(id=id)
        app.state.broker.delete_bot(bot['room'], bot)
        return JSONResponse(bot)


class ApiActionsClearRoomMessages(HTTPEndpoint):
    async def post(self, request: Request):
        """Clear all messages in a room."""
        try:
            data = await request.json()
        except json.JSONDecodeError:
            return JSONResponse({'message': 'Invalid JSON'}, status_code=400)

        if (room := data.get('room')) is None:
            return JSONResponse({'message': 'Need to provide the room name to clear the messages.'}, status_code=400)

        events.trigger_clear_room_messages(request.app.state.db, request.app.state.broker, room)
        return JSONResponse({'room': room})


class ApiActionsClearRoomState(HTTPEndpoint):
    async def post(self, request: Request):
        """Clear the state on a room by sending a blank system message."""
        try:
            data = await request.json()
        except json.JSONDecodeError:
            return JSONResponse({'message': 'Invalid JSON'}, status_code=400)

        if (room := data.get('room')) is None:
            return JSONResponse({'message': 'Need to provide the room name to clear the state of.'}, status_code=400)

        events.trigger_clear_room_state(request.app.state.db, request.app.state.broker, room)
        return JSONResponse({'room': room})


class WebSocketRoom(WebSocketEndpoint):
    """
    The websocket endpoint /ws/{room}?since_id=-1 will deliver a read-only stream of events from a room, after the given
    message id.
    """
    async def on_connect(self, ws: WebSocket):
        await ws.accept()

        room = ws.path_params['room']
        self.room = room

        # Parse since_id to an integer no matter what.
        since_id = -1
        try:
            since_id = int(ws.query_params.get('since', since_id))
        except:
            pass

        last_cleared_entry = ws.app.state.db.clears.find(room=room)
        last_cleared_id = last_cleared_entry['last_cleared_id'] if last_cleared_entry is not None else None

        should_clear = False
        if last_cleared_id is not None and last_cleared_id >= since_id:
            should_clear = True
            since_id = last_cleared_id

        current_bots = list(ws.app.state.db.bots.find_all(room=room))
        new_messages = list(ws.app.state.db.messages.since(room, since_id))
        recv, self.tag = ws.app.state.broker.subscribe(
            room=room,
            init_bots=current_bots,
            init_messages=new_messages,
            should_clear=should_clear,
        )

        asyncio.create_task(self.message_pump(ws, recv))

    async def on_disconnect(self, ws: WebSocket, close_code: int):
        logger.info(f"Websocket for room {self.room} closed with {close_code=}")
        ws.app.state.broker.unsubscribe(self.tag)

    async def message_pump(self, ws: WebSocket, messages):
        """
        Move messages from an anyio stream (a queue) into the websocket, until the stream closes.
        This should be spawned into a new task.
        """
        async for message in messages:
            await ws.send_json(message)


class NoCacheHeader(BaseHTTPMiddleware):
    """
    Adds a 'Cache-Control: no-cache' header to every HTTP response from the server. The behaviour of no-cache is that
    the browser may still choose to cache files, but must re-validate them with the server (via their etag, for example)
    upon each request.
    """
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers['Cache-Control'] = 'no-cache'
        return response



routes = [
    Route('/', Lobby),

    # Resources needed by the Lobby and Room endpoints (supporting HTML, JS, CSS).
    Mount('/client', app=StaticFiles(directory=BASE_DIR / 'client')),

    # The swagger-ui/ directory holds a copy of the dist/ directory from https://github.com/swagger-api/swagger-ui.
    # The swagger-initializer.js file has been updated to point at /api/spec.
    Mount('/docs', app=StaticFiles(directory=BASE_DIR / 'swagger-ui', html=True)),
    Route('/docs', Docs),
    Route('/api/spec', ApiSpec),

    # API endpoints which are GET routes accepting query parameters.
    Route('/api/messages', ApiMessages),
    Route('/api/bots', ApiBots),

    # API endpoints which are POST or DELETE routes accepting JSON payloads.
    Route('/api/actions/message', ApiActionsMessage),
    Route('/api/actions/message-form', ApiActionsMessageForm),
    Route('/api/actions/bot', ApiActionBot),
    Route('/api/actions/clear-room-messages', ApiActionsClearRoomMessages),
    Route('/api/actions/clear-room-state', ApiActionsClearRoomState),


    WebSocketRoute('/ws/{room:path}', WebSocketRoom),

    # This route must come last because it's a catch-all.
    Route('/{room:path}', Room),
]

middleware = [
    # I'm assuming that at some point we needed this cross-origin stuff on the API endpoints.
    # Here we heavy-handedly apply it across the whole application, an alternative would be wrapping
    # the API endpoints into their own app, and mounting that app perhaps?
    Middleware(CORSMiddleware, allow_origins=['*'], allow_methods=['*'], allow_headers=['*']),

    # Ensure that clients are always getting the freshest Necsus version.
    Middleware(NoCacheHeader),
]

app = Starlette(
    debug=True,
    routes=routes,
    middleware=middleware,
    lifespan=lifespan,
)
