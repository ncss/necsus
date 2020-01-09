import datetime
import pytz
import sqlite3

from pypika import Query, Table, Field

UTC = pytz.utc
SYDNEY = pytz.timezone('Australia/Sydney')

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
      # TODO: get id of created item
    except sqlite3.IntegrityError:
      # If the key is a duplicate
      # then update
      q = Query.update(self.table).where(self.table.id == kwargs['id'])
      for key, value in kwargs.items():
        if key != id:
          q = q.set(key, value)
      c.execute(q.get_sql())

    self.connection.commit()
    # TODO: return legit data instead of kwargs
    return kwargs

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
    return c.fetchone()


class Messages(DBList):
  table = Table('messages')
  allowed_keys = ['id', 'room', 'author', 'text', 'when', 'image', 'reply_to', 'state']

  def new(self, since_id, **kwargs):
    "Return a generator of messages since a given id (which may be None to return all messages)"

    messages = self.find_all(**kwargs)

    after_old_message = True if since_id == None else False
    for message in messages:
      if after_old_message:
        yield message
      if str(message['id']) == str(since_id):
        after_old_message = True

  def add(self, **message):
    now = UTC.localize(datetime.datetime.utcnow())
    local = now.astimezone(SYDNEY)
    message['when'] = local.strftime('%-I:%M%p').lower()

    c = self.connection.cursor()
    keys = [key for key in message.keys() if key in self.allowed_keys]
    values = [value for key,value in message.items() if key in self.allowed_keys]
    q = Query.into(self.table).columns(*keys).insert(*values)
    print('Executing:', q.get_sql())
    c.execute(q.get_sql())
    self.connection.commit()
    return message


  def room_state(self, room_name):
    "Return None if the room has no special state, otherwise (bot_id, state)"
    
    room_messages = self.find_all(room=room_name)
    if room_messages == []:
      return None
    
    last_message = room_messages[-1]
    if last_message['reply_to'] != None:
      return last_message['reply_to'], last_message['state']
    
    return None


class Bots(DBList):
  table = Table('bots')


class DB():
  def __init__(self, connection):
    self.messages = Messages(connection)
    self.bots = Bots(connection)

  def load_dummy_data(self):
    self.messages.add_if_new(room='', author='kenni', text='Welcome!')

    self.bots.add_if_new(room='', name='Echo', url='https://flask-endpoint-echo.kennib.repl.co')
    self.bots.add_if_new(room='', name='Repeat', responds_to='repeat (?P<word>\w+) (?P<count>\d+) times', url='https://repeat-bot.kennib.repl.co')
    self.bots.add_if_new(room='baking', name='I want to make', url='https://baking-assistant.kennib.repl.co/recipe')
    self.bots.add_if_new(room='games', name='roll', url='https://roll-bot.kennib.repl.co')
