from flask import request, redirect, render_template, send_from_directory
from neccsus import app, db
import events
import commands

@app.route('/')
@app.route('/client')
def client():
  return send_from_directory('client', 'index.html')

@app.route('/client/<path:path>')
def client_path(path):
  return send_from_directory('client', path)

@app.route('/form', methods=['GET'])
def form_page():
  author = db.members.find('kenni')
  messages = db.messages.list()
  return render_template('home.html', author=author, messages=messages)

@app.route('/form', methods=['POST'])
def form_accept():
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


