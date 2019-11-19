from flask import Flask, g
import db

import sqlite3

DATABASE = 'necsus.db'

app = Flask('NeCSuS')

def get_connection():
  connection = getattr(g, '_connection', None)
  if connection is None:
    connection = g._database = sqlite3.connect(DATABASE)
  return connection

def get_db():
  connection = get_connection()
  return db.DB(connection)

def init_db():
  with app.app_context():
    connection = get_connection()
    with app.open_resource('schema.sql', mode='r') as f:
      connection.cursor().executescript(f.read())
    connection.commit()

    get_db().load_dummy_data()

@app.teardown_appcontext
def close_connection(exception):
  connection = getattr(g, '_connection', None)
  if connection is not None:
    connection.close()
