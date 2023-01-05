from __future__ import annotations

from quart import request, jsonify, send_from_directory
from flask_swagger import swagger
from werkzeug.exceptions import HTTPException

import events
from necsus import app, get_db
from ws import broker

# from crossdomain import crossdomain



@app.route('/docs/')
@app.route('/docs/<path:path>')
async def swagger_ui(path: str | None = None):
  """
  The swagger-ui/ directory holds a copy of the dist/ directory from https://github.com/swagger-api/swagger-ui, with the
  swagger-initializer.js file updated to point at /api/spec. This endpoint just serves that directory.
  """
  return await send_from_directory('swagger-ui', path or 'index.html', cache_timeout=60*10)

@app.errorhandler(Exception)
async def handle_error(e):
    if isinstance(e, HTTPException):
        code = e.code
        message = e.description
    else:
      code = 500
      message = 'There was an internal server error.'
      app.logger.error(e)

    return jsonify({'error': code, 'message': message}), code

@app.route("/api/spec")
async def api_spec():
  """The swagger() function inspects the app for things that look like OpenAPI endpoints with YAML docstrings."""
  swag = swagger(app)
  swag['info']['version'] = '1.0'
  swag['info']['title'] = 'NeCSuS API'
  return jsonify(swag)

@app.route('/api/messages', methods=['GET'])
#@crossdomain(origin='*')
async def get_new_messages():
  """
        List messages
        ---
        tags:
          - messages
        parameters:
          - in: query
            name: room
            required: true
            schema:
              type: string
            description: the name of the room
          - in: query
            name: since
            schema:
              type: integer
            description: the ID of the last message you already have
        responses:
          200:
            description: Messages since last message
            schema:
              type: array
              items:
                schema:
                  id: Message
                  properties:
                    id:
                     type: integer
                     example: 1
                     description: the messages's unique ID
                    room:
                     type: string
                     example: tutors
                     description: the room the message was posted in
                    author:
                     type: string
                     example: Georgina
                     description: the author of the message
                    text:
                     type: string
                     example: Hello, World!
                     description: the message's text
  """
  since_id = request.args.get('since')
  room = request.args.get('room')

  if room is None:
    return jsonify({'message': 'room name is required'}), 400

  if since_id is not None:
    try:
      _ = int(since_id)
    except ValueError:
      return jsonify({'message': 'since_id must be an integer'}), 400

  db = await get_db()
  new_messages = list(db.messages.new(since_id, room=str(room)))

  return jsonify(new_messages)

@app.route('/api/bots', methods=['GET'])
#@crossdomain(origin='*')
async def get_bots():
  """
        List Bots
        ---
        tags:
          - bots
        parameters:
          - in: query
            name: room
            schema:
              type: string
            description: The name of the room to list bots for. If not provided, will list all registered bots.
        responses:
          200:
            description: Bots and their endpoints
            schema:
              type: array
              items:
                schema:
                  id: Bot
                  required:
                    - name
                    - responds_to
                    - room
                    - url
                  properties:
                    id:
                     type: integer
                     example: 1
                     description: the bot's unique ID
                    name:
                     type: string
                     example: NeCSuS Bot
                     description: the bot's name
                    responds_to:
                     type: string
                     example: "(?P<greeting>hi|hello)(?P<other>.*)"
                     description: regex that triggers sending the message to the bot
                    room:
                     type: string
                     example: my_room
                     description: room that the bot is registered in
                    url:
                     type: string
                     example: https://necsus-bot.ncss.cloud
                     description: the bot's url
  """
  room = request.args.get('room')

  db = await get_db()

  if room is not None:
    bots = list(db.bots.find_all(room=room))
    return jsonify(bots)
  else:
    bots = list(db.bots.find_all())
    return jsonify(bots)

@app.route('/api/actions/bot', methods=['POST'])
#@crossdomain(origin='*')
async def post_bot():
  """
        Create or Update a Bot
        ---
        tags:
          - bots
        parameters:
          - in: body
            name: content
            required: true
            schema:
              id: Bot

        responses:
          200:
            description: The created or updated bot
            schema:
              id: Bot
  """
  data = await request.get_json()

  # TODO: verify these; make nicer behaviour if bot with supplied id exists,
  # reject if will create new bot and missing fields.
  room = data.get('room')
  id = data.get('id')
  name = data.get('name')
  responds_to = data.get('responds_to')
  url = data.get('url')

  db = await get_db()
  bot = db.bots.update_or_add(id=id, room=room, name=name, responds_to=responds_to, url=url)
  broker.put_bot(room, bot)

  return jsonify(bot)

@app.route('/api/actions/bot', methods=['DELETE'])
#@crossdomain(origin='*')
async def delete_bot():
  """
        Remove a Bot
        ---
        tags:
          - bots
        parameters:
          - in: query
            name: id
            schema:
              type: integer
            description: ID of the bot to delete
        responses:
          200:
            description: bot was successfully removed
            schema:
              properties:
                id:
                 type: integer
                 example: 1
                 description: ID of the removed bot
  """
  id = request.args.get('id')

  if id is None:
    return jsonify({'message': 'id of a bot to remove is required'}), 400

  db = await get_db()
  found = db.bots.find(id=id)

  if not found:
    return jsonify({'message': 'bot with this id not found'}), 404

  db.bots.remove(id=id)
  broker.delete_bot(found['room'], found)
  return jsonify(found)

@app.route('/api/actions/message', methods=['POST'])
#@crossdomain(origin='*')
async def post_message():
  """
        Post a message to a room
        ---
        tags:
          - messages
        parameters:
          - in: body
            name: content
            required: true
            schema:
              type: object
              required:
                - room
                - author
                - text
              properties:
                room:
                  type: string
                  example: 'party-room'
                author:
                  type: string
                  nullable: true
                  example: 'Kenni'
                text:
                  type: string
                  example: 'Hello sam'

        responses:
          200:
            description: The message was successfully posted.
            schema:
              id: Message
  """

  data = await request.get_json()
  if not data:
    return jsonify({'message': 'message must be valid JSON object'}), 400

  text, room, author = [data.get(key) for key in ['text', 'room', 'author']]
  if text is None or room is None or author is None:
    return jsonify({'message': 'text, room, and author keys must be present and non-empty'}), 400

  message = events.trigger_message_post(await get_db(), room, author, text)
  return jsonify(message)

@app.route('/api/actions/clear-room-state', methods=['POST'])
#@crossdomain(origin='*')
async def clear_room_state():
  """
        Clear any pending conversation state on a room
        ---
        tags:
          - room
        parameters:
          - in: query
            name: room
            schema:
              type: string
        responses:
          200:
            description: Room
            schema:
              id: Message
              properties:
                room:
                 type: string
                 example: tutors
                 description: the room that had its state cleared
  """

  data = await request.values
  room = data['room']
  db = await get_db()
  events.trigger_clear_room_state(db, room)
  return jsonify({'room': room})

@app.route('/api/actions/clear-room-messages', methods=['POST'])
#@crossdomain(origin='*')
async def clear_room_messages():
  """
        Remove a room's messages
        ---
        tags:
          - room
        parameters:
          - in: body
            description: the room to clear
            name: content
            required: true
            schema:
              type: object
              required:
                - room
              properties:
                room:
                  type: string
                  example: my_room

        responses:
          200:
            description: room messages successfully cleared
            schema:
              properties:
                room:
                  type: string
                  example: tutors
                  description: the room that was cleared
  """

  data = await request.get_json()

  if not data or data.get('room') is None:
    return jsonify({'message': 'room name is required'}), 400

  db = await get_db()
  room = events.trigger_clear_room_messages(db, str(data.get('room')))

  return jsonify({'room': room})
