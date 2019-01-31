from flask import request, jsonify
from crossdomain import crossdomain
from neccsus import app, db

import events 

@app.route('/api/endpoint', methods=['POST'])
def endpoint():
  url = request.values.get('url')
  endpoint = db.endpoints.set(url)
  return jsonify(endpoint)

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
  command = commands.parse(message.get('text'))
  message_result = events.trigger_command(message, command)
  return jsonify(message_result)
