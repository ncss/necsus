from quart import request, redirect, render_template, send_from_directory

import events
from necsus import app, db


@app.route('/client/<path:path>')
async def client_path(path):
  return await send_from_directory('client', path)

@app.route('/')
async def lobby():
  return await send_from_directory('client', 'lobby.html')

@app.route('/<room>')
async def client(room):
  return await send_from_directory('client', 'index.html')

# @app.route('/api', methods=['GET'])
# async def api():
#   endpoints = db.endpoints.find()
#   return render_template('api.html', endpoints=endpoints)
#
# @app.route('/interaction', methods=['POST'])
# def interaction():
#   params = dict(request.values)
#   events.trigger_interaction(params)
#
#   return redirect('/', code=302)
