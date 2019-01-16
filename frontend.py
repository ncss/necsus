from flask import request, redirect, render_template
from neccsus import app, db
import commands
import interactivity 

@app.route('/', methods=['GET'])
def home():
  author = db.members.find('kenni')
  messages = db.messages.list()
  return render_template('home.html', author=author, messages=messages)

@app.route('/', methods=['POST'])
def home_message():
  message = dict(request.values)

  if message.get('reponse_type') == 'in_channel':
    message_result = db.messages.add(**message)

  command = commands.parse(message['text'])
  if command:
    name, text = command 
    reply_message = commands.run(name, text)
    reply_message_result = db.messages.add(**reply_message)

  return redirect('/', code=302)

@app.route('/api', methods=['GET'])
def api():
  endpoints = db.endpoints.find()
  return render_template('api.html', endpoints=endpoints)

@app.route('/interaction', methods=['POST'])
def interaction():
  params = dict(request.values)
  reply_message = interactivity.interact(params)
  reply_message_result = db.messages.add(**reply_message)

  return redirect('/', code=302)


