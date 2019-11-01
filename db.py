import sqlite3

class DBList(dict):
  data = []

  def list(self):
    return self.data

  def find(self, **kwargs):
    return next(self.find_all(**kwargs), None)

  def find_all(self, **kwargs):
    for item in self.data:
      if all(item.get(key) == value for key, value in kwargs.items()):
        yield item

  def add(self, **kwargs):
    if kwargs.get('id') == None:
      kwargs['id'] = str(len(self.data))

    itemClass = type(self)
    item = itemClass(**kwargs)
    self.data.append(item)
    return item

  def remove(self, id):
    item = self.find(id=id)
    self.data.remove(item)

class Member(DBList):
  data = []

class Message(DBList):
  data = []

  def new(self, since_id, **kwargs):
    messages = self.find_all(**kwargs)

    after_old_message = True if since_id == None else False
    for message in messages:
      if after_old_message:
        yield message
      if message['id'] == since_id:
        after_old_message = True

class Bot(DBList):
  data = []

  def set(self, id=None, room=None, name=None, url=None):
    existing_bot = self.find(id=id)

    if existing_bot:
      existing_bot.update({
        'room': room,
        'name': name,
        'url': url,
      })
      return existing_bot 

    else:
      return self.add(id=id, room=room, name=name, url=url)

members = Member() 
messages = Message()
bots = Bot()

members.add(id='kenni')
members.add(id='necsus')
members.add(id='necsus-bot')

messages.add(room='', author='necsus', text='Hello, World!')
messages.add(room='', author='kenni', text='Yo!')

bots.set(room='', name='necsus-bot', url='https://neccsus-bot.herokuapp.com/neccsus/command')
bots.set(room='', name='Echo', url='https://flask-endpoint-echo.kennib.repl.co')
bots.set(room='', name='Repeat', url='https://flask-endpoint-echo.kennib.repl.co')
bots.set(room='baking', name='I want to make', url='https://baking-assistant.kennib.repl.co/recipe')
