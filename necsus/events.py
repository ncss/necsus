"""
Events contains the business logic for receiving messages and dispatching them to bots.
"""
import html
import json
import re

import httpx


class BotException(Exception):
    """An exception type for when we can tell what is probably going wrong with a bot."""


def system_message(room: str, text: str):
    """Helper function for returning system messages (with a fixed name and kind)."""
    return {
        'author': 'NeCSuS',
        'room': room,
        'text': text,
        'kind': 'system',
    }


async def trigger_message_post(db, broker, room: str, author: str, text: str):
    special_state = db.messages.room_state(room_name=room)
    message = db.messages.add(room=room, author=author, text=text)
    broker.publish_message(room, message)

    if special_state:
        bot_id, state = special_state
        bots = db.bots.find_all(id=bot_id)
        if len(bots) != 1:
            return message

        bot = bots[0]
        await trigger_bot(db, broker, room, author, text, bot, {}, state=state)
    else:
        await match_and_trigger_bots(db, broker, room, author, text)

    return message


def trigger_clear_room_state(db, broker, room: str):
    """Post an emptyish message to a room to clear any state left over from the last
    message. This is meant to be used for debugging and development purposes."""

    if db.messages.room_state(room_name=room):
        message = system_message(room, 'The room state has been cleared')
        db.messages.add(**message)
        broker.publish_message(room, message)


async def match_and_trigger_bots(db, broker, room: str, author: str, text: str) -> None:
    room_bots = db.bots.find_all(room=room)

    for bot in room_bots:
        search = bot.get('responds_to') or bot.get('name')
        try:
            match = re.search(search, text, flags=re.IGNORECASE)
        except:
            name = bot.get('name')
            t = 'responds_to' if bot.get('responds_to') else 'name'
            message = system_message(room=room, text=f'Something went wrong. Bot {name!r} has an invalid {t} regex: <pre>{search}</pre>')
            db.messages.add(**message)
            broker.publish_message(room, message)
            continue

        if search and match:
            await trigger_bot(db, broker, room, author, text, bot, match.groupdict())


async def trigger_bot(db, broker, room: str, author: str, text: str, bot, params, state=None) -> None:
    try:
        reply = await run_bot(room, bot, text, params, user=author, state=state)
    except Exception as e:
        error_message = f"<p>Error when running bot {bot['name']}: {type(e).__name__}: {e}.</p>"
        if (f := e.__cause__) is not None:
            error_message += f"Further information: {type(f).__name__}: {f}."

        message = system_message(room, error_message)
        db.messages.add(**message)
        broker.publish_message(room, message)
        return

    reply = db.messages.add(**reply)
    broker.publish_message(room, reply)


def trigger_clear_room_messages(db, broker, room):
    if (msg := db.messages.last(room=room)) is not None:
        db.clears.set_last_cleared_id(room=room, last_cleared_id=msg['id'])
        db.messages.delete(room=room)
        broker.clear_room(room)

    return room


# Timeout before ignoring a bot and considering it unresponsive, in seconds.
BOT_TIMEOUT = httpx.Timeout(15.0)


async def run_bot(room, bot, text, params, user=None, state=None):
    """
    Contact a bot using a POST request. Either returns a valid message from that bot to be inserted into the room,
    or raises a BotException.
    """
    name = bot.get('name', 'bot')
    if not (endpoint_url := bot.get('url')):
        raise BotException("The bot has an empty endpoint URL.")

    data = {
        'room': room,
        'author': user,
        'text': text,
        'params': params,
    }

    if state is not None:
        data['state'] = state

    try:
        async with httpx.AsyncClient() as client:
            reply = await client.post(endpoint_url, json=data, timeout=BOT_TIMEOUT)
    except httpx.ConnectError as e:
        raise BotException(f"Could not connect to {bot['name']} at the endpoint {endpoint_url!r}. Is the URL correct?") from e
    except httpx.TimeoutException as e:
        raise BotException(f"The bot {bot['name']} timed out after {BOT_TIMEOUT.read} seconds(s)") from e

    if reply.status_code != httpx.codes.OK:
        raise BotException(f"The bot {bot['name']} responded with a non-ok status code of {reply.status_code}")

    try:
        message = reply.json()
    except json.decoder.JSONDecodeError as e:
        raise BotException(f"The bot {bot['name']} responded with status code {reply.status_code}, but returned invalid JSON: <pre>{html.escape(reply.text)}</pre>") from e

    safe_message = {}
    if isinstance(message, dict) and 'text' in message and isinstance(message['text'], str):
        safe_message['text'] = message['text']
    else:
        raise BotException(f"The bot {bot['name']} responded, but was missing a 'text' key of type string")

    if 'author' in message and isinstance(message['author'], str):
        safe_message['author'] = message['author']
    else:
        safe_message['author'] = name

    if 'room' in message and isinstance(message['room'], str):
        safe_message['room'] = message['room']
    else:
        safe_message['room'] = room

    if 'state' in message and message['state'] != None:
        safe_message['state'] = message['state']
        safe_message['reply_to'] = bot.get('id')

    if 'image' in message and isinstance(message['image'], str):
        safe_message['image'] = message['image']

    if 'media' in message and isinstance(message['media'], str):
        safe_message['media'] = message['media']

    safe_message['kind'] = 'bot'
    return safe_message
