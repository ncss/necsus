import json
import sqlite3
import time

import pypika
from pypika import Query, Table


class DBList(dict):
  table = Table('')

  def __init__(self, connection):
    self.connection = connection
    self.connection.row_factory = lambda x,y: dict(sqlite3.Row(x,y))

  def _find(self, **kwargs):
    c = self.connection.cursor()

    search = [getattr(self.table, key) == value for key, value in kwargs.items()]
    q = Query.from_(self.table).select(self.table.star)
    for condition in search:
      q = q.where(condition)

    c.execute(q.get_sql())
    return c

  def find(self, **kwargs):
    return self._find(**kwargs).fetchone()

  def find_all(self, **kwargs):
    return self._find(**kwargs).fetchall()

  def add(self, **kwargs):
    c = self.connection.cursor()
    q = Query.into(self.table).columns(*kwargs.keys()).insert(*kwargs.values())
    c.execute(q.get_sql())
    self.connection.commit()
    return kwargs

  def update_or_add(self, **kwargs):
    c = self.connection.cursor()

    try:
      # Try to add
      q = Query.into(self.table)\
      .columns(*kwargs.keys())\
      .insert(*kwargs.values())
      c.execute(q.get_sql())
      kwargs['id'] = c.lastrowid
    except sqlite3.IntegrityError:
      # If the key is a duplicate
      # then update
      q = Query.update(self.table).where(self.table.id == kwargs['id'])
      for key, value in kwargs.items():
        if key != id:
          q = q.set(key, value)
      c.execute(q.get_sql())

    self.connection.commit()
    return self.find(id=kwargs['id'])

  def add_if_new(self, **kwargs):
    c = self.connection.cursor()

    search = [getattr(self.table, key) == value for key, value in kwargs.items()]
    q = Query.from_(self.table).select(self.table.star)
    for condition in search:
      q = q.where(condition)
    c.execute(q.get_sql())

    result = c.fetchone()
    new = result == None

    if new:
      q = Query.into(self.table)\
      .columns(*kwargs.keys())\
      .insert(*kwargs.values())
      c.execute(q.get_sql())

    self.connection.commit()
    return kwargs

  def delete(self, **kwargs):
    c = self.connection.cursor()

    search = [getattr(self.table, key) == value for key, value in kwargs.items()]
    q = Query.from_(self.table).delete()
    for condition in search:
      q = q.where(condition)
    c.execute(q.get_sql())
    self.connection.commit()

    return c.fetchone()

  def remove(self, id):
    c = self.connection.cursor()
    q = Query.from_(self.table).delete().where(self.table.id == id)
    c.execute(q.get_sql())
    self.connection.commit()
    return c.rowcount > 0


class Messages(DBList):
  table = Table('messages')
  allowed_keys = ['id', 'room', 'author', 'kind', 'text', 'when', 'image', 'media', 'mjs', 'css', 'from_bot', 'state']

  def since(self, room: str, since_id: int = -1):
    """Return a list of all messages in the room with IDs strictly greater than a given ID, in ascending ID order."""
    query = (
      Query
      .from_(self.table)
      .select(self.table.star)
      .where(self.table.room == room)
      .where(self.table.id > since_id)
      .orderby('id')
    )
    c = self.connection.cursor()
    c.execute(query.get_sql())
    return c.fetchall()

  def last(self, room: str):
    """Return the most recent message in the room."""
    query = (
      Query
      .from_(self.table)
      .select(self.table.star)
      .where(self.table.room == room)
      .orderby('id', order=pypika.Order.desc)
      .limit(1)
    )
    c = self.connection.cursor()
    c.execute(query.get_sql())
    message = c.fetchone()
    return message


  def add(self, **message):
    now = time.time()
    message['when'] = now
    if message.get('state', None) != None:
      message['state'] = json.dumps(message['state'])

    c = self.connection.cursor()
    keys = [key for key in message.keys() if key in self.allowed_keys]
    values = [value for key,value in message.items() if key in self.allowed_keys]
    q = Query.into(self.table).columns(*keys).insert(*values)
    c.execute(q.get_sql())
    self.connection.commit()
    return self.last(room=message['room'])


  def room_state(self, room_name):
    "Return None if the room has no special state, otherwise (bot_id, state)"

    room_messages = self.find_all(room=room_name)
    if room_messages == []:
      return None

    last_message = room_messages[-1]
    if last_message['state'] != None:
      state = json.loads(last_message.get('state', None))
      return last_message['from_bot'], state

    return None


class Bots(DBList):
  table = Table('bots')


class Clears(DBList):
  table = Table('clears')

  def set_last_cleared_id(self, room: str, last_cleared_id: int):
    if self.find(room=room) is None:
      self.add(room=room, last_cleared_id=last_cleared_id)
    else:
      c = self.connection.cursor()
      q = Query.update(self.table).where(self.table.room == room).set('last_cleared_id', last_cleared_id)
      c.execute(q.get_sql())
      self.connection.commit()


class DB():
  def __init__(self, connection):
    self._connection = connection
    self.messages = Messages(connection)
    self.bots = Bots(connection)
    self.clears = Clears(connection)
