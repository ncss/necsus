from flask import request, jsonify
from crossdomain import crossdomain
from necsus import app, db

import events 

@app.route('/api/messages', methods=['GET'])
@crossdomain(origin='*')
def get_new_messages():
  since_id = request.values.get('since')
  room = request.values.get('room')

  new_messages = list(db.messages.new(since_id, room=room))

  return jsonify(new_messages)

@app.route('/api/bots', methods=['GET'])
@crossdomain(origin='*')
def get_bots():
  room = request.values.get('room')

  if room != None:
    bots = list(db.bots.find_all(room=room))
    return jsonify(bots)
  else:
    bot = db.bots.list() 
    return jsonify(bot)

@app.route('/api/actions/bot', methods=['POST'])
@crossdomain(origin='*')
def post_bot():
  room = request.values.get('room')
  id = request.values.get('id')
  name = request.values.get('name')
  url = request.values.get('url')
  bot = db.bots.set(id=id, room=room, name=name, url=url)
  return jsonify(bot)

@app.route('/api/actions/bot', methods=['DELETE'])
@crossdomain(origin='*')
def delete_bot():
  id = request.values.get('id')
  bot = db.bots.remove(id)
  return jsonify({id: id})

@app.route('/api/actions/message', methods=['POST'])
@crossdomain(origin='*')
def post_message():
  message = dict(request.values)
  message_result = events.trigger_message_post(message)
  return jsonify(message_result)
