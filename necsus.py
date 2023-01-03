import sqlite3

from quart import Quart, g

import db

DATABASE = 'necsus.db'

app = Quart('NeCSuS')

async def get_connection():
  connection = getattr(g, '_connection', None)
  if connection is None:
    connection = g._database = sqlite3.connect(DATABASE)
  return connection

async def get_db():
  connection = await get_connection()
  return db.DB(connection)

@app.before_first_request
async def init_db():
  async with app.app_context():
    connection = await get_connection()
    async with await app.open_resource('schema.sql', mode='r') as f:
      connection.cursor().executescript(await f.read())
    connection.commit()

@app.teardown_appcontext
def close_connection(exception):
  connection = getattr(g, '_connection', None)
  if connection is not None:
    connection.close()
