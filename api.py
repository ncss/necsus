from flask import request, jsonify
from crossdomain import crossdomain
from neccsus import app, db

import events, commands

@app.route('/api/bot', methods=['POST'])
def bot():
  room = request.values.get('room')
  name = request.values.get('name')
  url = request.values.get('url')
  bot = db.bots.set(room=room, name=name, url=url)
  return jsonify(bot)

@app.route('/api/actions/message', methods=['GET'])
@crossdomain(origin='*')
def get_message():
  message_id = request.values.get('id')

  if message_id:
    message = db.messages.find(message_id) 
    return jsonify(message)
  else:
    messages = db.messages.list() 
    return jsonify(messages)

@app.route('/api/actions/message', methods=['POST'])
@crossdomain(origin='*')
def post_message():
  message = dict(request.values)
  message_result = events.trigger_message_post(message)
  return jsonify(message_result)

@app.route('/api/actions/command', methods=['POST'])
@crossdomain(origin='*')
def do_command():
  message = dict(request.values)
  command = message.get('command')
  text = message.get('text')
  endpoint = message.get('endpoint')
  user = message.get('author')
  room = message.get('room', '')
  bot = db.bots.find(room=room, name=command) or {'room': room, 'name': command, 'url': endpoint}

  message_result = events.trigger_command(message, bot, text, user=user)
  return jsonify(message_result)
