"""
Events contains the business logic for receiving messages and dispatching them to bots.
"""
import html
import json
import re
import urllib.parse

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


def standard_message_for_bot(room: str, author: str, text: str, params=None, state=None):
    message = dict(room=room, author=author, text=text, params=params or {})
    if state is not None:
        message['state'] = state

    return message


async def trigger_message_post(db, broker, room: str, author: str, text: str, image, media):
    special_state = db.messages.room_state(room_name=room)
    message = db.messages.add(room=room, author=author, text=text, image=image, media=media)
    broker.publish_message(room, message)

    if special_state:
        bot_id, state = special_state
        bots = db.bots.find_all(id=bot_id)
        if len(bots) != 1:
            return message

        bot = bots[0]
        msg = standard_message_for_bot(room=room, author=author, text=text, params={}, state=state)
        reply = await trigger_bot(room, bot, msg)
        reply = db.messages.add(**reply)
        broker.publish_message(room, reply)
    else:
        await match_and_trigger_bots(db, broker, room, author, text)

    return message


async def trigger_message_form_post(db, broker, room: str, author: str, bot_id: int, action_url: str, form_data):
    bot = db.bots.find(id=bot_id)
    if bot is None:
        error = system_message(room, f"The bot associated to that form can't be found - perhaps it was deleted?")
        db.messages.add(**error)
        broker.publish_message(room, error)
        return

    # We want the action_url to be relative to the bot's endpoint. For instance, say that the bot is at
    # http://bot.com/foo/bar, then the following URLs should tranform like
    #  (action_url = /baz) => http://bot.com/baz
    #  (action_url = baz) => http://bot.com/foo/baz
    #  (action_url = http://example.com/what) => http://example.com/what
    url = urllib.parse.urljoin(bot['url'], action_url)

    # Either fetch the bot with this URL, or create a new transient bot which has no ID.
    to_bot = db.bots.find(room=room, url=url) or {'room': room, 'name': url, 'url': url}
    msg = {'room': room, 'author': author, 'form_data': form_data}
    special_state = db.messages.room_state(room_name=room)
    if special_state is not None:
        _, state = special_state
        msg['state'] = state

    reply = await trigger_bot(room, to_bot, msg)

    # If this new bot replied with some conversation state, but it's not installed into the room, let's just make up a
    # new bot so that we can put an ID in the from_bot field.
    if reply.get('state') is not None and to_bot.get('id') is None:
        db.bots.add(room=room, name=f"(Auto) {url}", url=url)
        to_bot = db.bots.find(room=room, url=url)
        broker.put_bot(room, to_bot)
        reply['from_bot'] = to_bot['id']

    print("Reply before:", reply)
    reply = db.messages.add(**reply)
    print("Reply after:", reply)
    broker.publish_message(room, reply)


def trigger_clear_room_state(db, broker, room: str):
    """Post an emptyish message to a room to clear any state left over from the last
    message. This is meant to be used for debugging and development purposes."""

    if db.messages.room_state(room_name=room):
        message = system_message(room, 'The room state has been cleared')
        message = db.messages.add(**message)
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
            message = db.messages.add(**message)
            broker.publish_message(room, message)
            continue

        if search and match:
            msg = standard_message_for_bot(room=room, author=author, text=text, params=match.groupdict())
            reply = await trigger_bot(room, bot, msg)
            reply = db.messages.add(**reply)
            broker.publish_message(room, reply)


async def trigger_bot(room: str, bot, msg):
    """
    Trigger a bot, sending msg to it in JSON-encoded POST data.
    Return either the message from the bot, or a system error message.
    """
    try:
        return await run_bot(room, bot, msg)
    except Exception as e:
        error_message = f"<p>Error when running bot {bot['name']}: {type(e).__name__}: {e}.</p>"
        if (f := e.__cause__) is not None:
            error_message += f"Further information: {type(f).__name__}: {f}."

        return system_message(room, error_message)


def trigger_clear_room_messages(db, broker, room):
    if (msg := db.messages.last(room=room)) is not None:
        db.clears.set_last_cleared_id(room=room, last_cleared_id=msg['id'])
        db.messages.delete(room=room)
        broker.clear_room(room)

    return room


# Timeout before ignoring a bot and considering it unresponsive, in seconds.
BOT_TIMEOUT = httpx.Timeout(15.0)


async def run_bot(room: str, bot, msg):
    """
    Contact a bot using a POST request. Either returns a valid message from that bot to be inserted into the room,
    or raises a BotException.
    """
    name = bot.get('name', 'bot')
    if not (endpoint_url := bot.get('url')):
        raise BotException("The bot has an empty endpoint URL.")

    try:
        async with httpx.AsyncClient() as client:
            reply = await client.post(endpoint_url, json=msg, timeout=BOT_TIMEOUT)
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

    # TODO(Joel): We should not allow a bot to override which room it is posting back to.
    if 'room' in message and isinstance(message['room'], str):
        safe_message['room'] = message['room']
    else:
        safe_message['room'] = room

    if 'state' in message and message['state'] != None:
        safe_message['state'] = message['state']

    if 'image' in message and isinstance(message['image'], str):
        safe_message['image'] = urllib.parse.urljoin(bot['url'], message['image'])

    if 'media' in message and isinstance(message['media'], str):
        safe_message['media'] = urllib.parse.urljoin(bot['url'], message['media'])

    if 'js' in message and isinstance(message['js'], str):
        safe_message['js'] = urllib.parse.urljoin(bot['url'], message['js'])

    if 'css' in message and isinstance(message['css'], str):
        safe_message['css'] = urllib.parse.urljoin(bot['url'], message['css'])

    safe_message['kind'] = 'bot'
    safe_message['from_bot'] = bot.get('id')
    return safe_message
