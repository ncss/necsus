from quart import request, redirect, render_template, send_from_directory

import events
from necsus import app, db


@app.route('/client/<path:path>')
async def client_path(path):
  return await send_from_directory('client', path, cache_timeout=0)

@app.route('/')
async def lobby():
  return await send_from_directory('client', 'lobby.html')

@app.route('/<room>')
async def client(room):
  return await send_from_directory('client', 'index.html')
