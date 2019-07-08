from flask import request, redirect, render_template
from neccsus import app, db
import events
import commands

@app.route('/', methods=['GET'])
def home():
  author = db.members.find('kenni')
  messages = db.messages.list()
  return render_template('home.html', author=author, messages=messages)

@app.route('/client', methods=['GET'])
def client():
  return open('client/index.html').read()

@app.route('/', methods=['POST'])
def home_message():
  message = dict(request.values)

  command = commands.parse(message.get('text'))
  if command:
    events.trigger_command(message, command)
  else:
    events.trigger_message_post(message)

  return redirect('/', code=302)

@app.route('/api', methods=['GET'])
def api():
  endpoints = db.endpoints.find()
  return render_template('api.html', endpoints=endpoints)

@app.route('/interaction', methods=['POST'])
def interaction():
  params = dict(request.values)
  events.trigger_interaction(params)

  return redirect('/', code=302)


