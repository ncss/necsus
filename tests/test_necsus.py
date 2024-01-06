import json
import pathlib
import subprocess

import asgiref.wsgi
import httpx
import pytest
import respx
from starlette.testclient import TestClient

from example_bots import app as example_bots_app
from necsus import app as necsus_app
from necsus.server import create_db_connection

# The necsus() fixture resets the database for each test, so this room should always start empty.
TEST_ROOM = 'test_room'
TEST_AUTHOR = 'TestAuthor'
EXAMPLE_BOTS_URL = 'http://localhost:12345'


@pytest.fixture
def necsus() -> TestClient:
    """
    Return a TestClient (fake web server for testing) for Necsus.
    We have set NECSUS_DB=:memory: in conftest.py, so this fixture returns a clean database in each test.
    """
    with TestClient(necsus_app) as necsus:
        yield necsus


@pytest.fixture
def example_bots() -> respx.MockRouter:
    with respx.mock(base_url=EXAMPLE_BOTS_URL) as respx_mock:
        # Joel: One would think we could just use respx.WSGIHandler(flask_app) rather than doing this conversion.
        #       It doesn't work: some difference deep in httpx or respx, to do with WSGITransport and an AsyncClient.
        example_bots_asgi_app = asgiref.wsgi.WsgiToAsgi(example_bots_app)
        yield respx_mock.route().mock(side_effect=respx.ASGIHandler(example_bots_asgi_app))


def test_necsus_fixture(necsus: TestClient):
    """Test that the TestClient fixture for the NeCSuS server is working."""
    response = necsus.get('/')
    assert response.status_code == 200


@pytest.mark.parametrize('anyio_backend', [('asyncio', {'use_uvloop': True})])
async def test_example_bots_fixture(anyio_backend, example_bots: respx.MockRouter):
    """Test that the MockRouter fixture for example bots is working."""
    async with httpx.AsyncClient() as client:
        response = await client.post(f'{EXAMPLE_BOTS_URL}/hellobot', json={})

    assert response.status_code == 200
    assert response.json()['text'] == 'Hello, world!'


def test_post_clear_messages(necsus: TestClient):
    """
    Test that we can post messages into a room, retrieve them, and clear the room. This test exercises:
    - GET /api/messages
    - POST /api/actions/message
    - POST /api/actions/clear-room-messages
    """

    # Ensure the room is empty to start with.
    assert necsus.get('/api/messages', params={'room': TEST_ROOM}).json() == []

    # Post a message, ensuring the returned message from the server has the same fields (and more) as our message.
    user_message = {'room': TEST_ROOM, 'author': TEST_AUTHOR, 'text': 'Hello there.'}
    server_message = necsus.post('/api/actions/message', json=user_message).json()
    assert user_message.items() <= server_message.items()

    # Ensure the message is in the room.
    assert necsus.get('/api/messages', params={'room': TEST_ROOM}).json() == [server_message]

    # Clear the room, and ensure there is nothing remaining.
    assert necsus.post('/api/actions/clear-room-messages', json={'room': TEST_ROOM}).status_code == 200
    assert necsus.get('/api/messages', params={'room': TEST_ROOM}).json() == []


def test_add_remove_bots(necsus: TestClient):
    """
    Test that we can add a bot to a room and remove it again. This test exercises:
    - GET /api/bots
    - POST, DELETE /api/actions/bot
    """

    # Ensure there are no bots in the room.
    assert necsus.get('/api/bots', params={'room': TEST_ROOM}).json() == []

    # Add a bot, ensuring the returned bot has the same fields (and more) as our bot.
    user_bot = {'room': TEST_ROOM, 'name': 'TestBot', 'url': 'http://definitely/a/url'}
    server_bot = necsus.post('/api/actions/bot', json=user_bot).json()
    assert user_bot.items() <= server_bot.items()

    # Ensure the bot is in the room.
    assert necsus.get('/api/bots', params={'room': TEST_ROOM}).json() == [server_bot]

    # Remove the bot from the room, and ensure there are no bots remaining.
    assert necsus.request('delete', '/api/actions/bot', json={'id': server_bot['id']}).status_code == 200
    assert necsus.get('/api/bots', params={'room': TEST_ROOM}).json() == []


def test_echo(necsus: TestClient, example_bots: respx.MockRouter):
    """
    Test a full round-trip on EchoBot, which checks:

    - Asserting the room has no bots to begin with.
    - Installing EchoBot into a room (with no responds-to, so it should only respond to its name).
    - Verifying EchoBot is in the room.
    - Posting a message which should not trigger the bot.
    - Posting a message which should trigger the bot.
    - Verifying the JSON sent to and from the bot.
    - Verifying the final message posted back to the room.
    """

    # Assert the room is empty to begin with (of both messages and bots).
    assert necsus.get('/api/messages', params={'room': TEST_ROOM}).json() == []
    assert necsus.get('/api/bots', params={'room': TEST_ROOM}).json() == []

    # Install the bot.
    response = necsus.post('/api/actions/bot', json={
            'room': TEST_ROOM,
            'name': 'EchoBot',
            'url': f'{EXAMPLE_BOTS_URL}/echobot',
        },
    )
    assert response.status_code == 200
    bot_id = response.json()['id']

    # Check the bot shows up in the API.
    assert necsus.get('/api/bots', params={'room': TEST_ROOM}).json() == [
        {
            'id': bot_id,
            'room': TEST_ROOM,
            'name': 'EchoBot',
            'responds_to': None,
            'url': f'{EXAMPLE_BOTS_URL}/echobot'
        },
    ]

    # Post a message which should not trigger the bot.
    necsus.post('/api/actions/message', json={'room': TEST_ROOM, 'author': 'Joel', 'text': 'Hello there.'})
    assert len(example_bots.calls) == 0

    # Trigger a message to the bot.
    user_message = {'room': TEST_ROOM, 'author': 'Joel', 'text': 'Hello there, echobot.'}
    response = necsus.post('/api/actions/message', json=user_message)

    # Check that the bot got a message of the right shape.
    bot_request = example_bots.calls.last.request
    assert bot_request.method == 'POST'
    bot_json = json.loads(bot_request.content)
    assert bot_json == {
        'room': TEST_ROOM,
        'author': 'Joel',
        'text': 'Hello there, echobot.',
        'params': {},
    }

    # Check that the bot responded correctly.
    bot_response = example_bots.calls.last.response
    assert bot_response.status_code == 200

    # Check that our final message post returned successfully.
    assert response.status_code == 200

    # Message subset that we expect in reply.
    expected_reply = {
        'room': TEST_ROOM,
        'author': 'EchoBot',
        'kind': 'bot',
        'text': 'Hello there, echobot.',
        'image': None,
        'media': None,
        'from_bot': bot_id,
        'state': None,
    }

    # Check that the message made it back to the room.
    messages = necsus.get('/api/messages', params={'room': TEST_ROOM}).json()
    assert len(messages) == 3
    assert user_message.items() <= messages[-2].items()
    assert expected_reply.items() <= messages[-1].items()


def test_schema(tmp_path: pathlib.Path):
    """
    The database Schema had a strange issue with double-quote and single-quote confusion, which led to internal errors
    in Sqlite3 when trying to take backups.
    """

    # Create an empty database on disk, initialised with the NeCSuS schema.
    db_path = str(tmp_path / 'necsus.db')
    create_db_connection(db_path).close()

    # Attempt to run a backup of it using the Sqlite3 CLI (for some reason this error does not happen in Python).
    backup_path = str(tmp_path / 'necsus.backup.db')
    backup_result = subprocess.run(['sqlite3', db_path, f"""VACUUM INTO '{backup_path}'"""])
    assert backup_result.returncode == 0


@pytest.mark.parametrize('bot_url,resource_url,expected_absolute_url', [
    (f'{EXAMPLE_BOTS_URL}/path/to/relbot', 'resource', f'{EXAMPLE_BOTS_URL}/path/to/resource'),
    (f'{EXAMPLE_BOTS_URL}/path/to/relbot', '/resource', f'{EXAMPLE_BOTS_URL}/resource'),
    (f'{EXAMPLE_BOTS_URL}/path/to/relbot', 'http://some.other.place/resource', 'http://some.other.place/resource'),
])
def test_relative_urls(bot_url: str, resource_url: str, expected_absolute_url: str, necsus: TestClient):
    """Check that the image, media, css, and mjs items are correctly relativised to the bot's URL."""
    with respx.mock:
        # Mock a response from our bot.
        route = respx.post(bot_url).mock(return_value=httpx.Response(
            status_code=200,
            json={
                'text': 'Hello there',
                'image': resource_url,
                'media': resource_url,
                'css': resource_url,
                'js': resource_url,
            }
        ))

        # Install the bot, post a message to it, and grab the reply as the last message in the room.
        necsus.post('/api/actions/bot', json={'room': TEST_ROOM, 'name': 'RelBot', 'url': bot_url})
        necsus.post('/api/actions/message', json={'room': TEST_ROOM, 'author': TEST_AUTHOR, 'text': 'Hi RelBot'})
        assert route.called
        last_message = necsus.get('/api/messages', params={'room': TEST_ROOM}).json()[-1]

        # Check that the resources have the correct modified absolute URL.
        for field in ['image', 'media', 'css', 'js']:
            assert last_message[field] == expected_absolute_url, field
