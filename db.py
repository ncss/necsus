import sqlite3

class DBList(dict):
  data = []

  def list(self):
    return self.data

  def find(self, **kwargs):
    return next(self.find_all(**kwargs), None)

  def find_all(self, **kwargs):
    yield next((item for item in self.data if all((item.get(key) == value for key, value in kwargs.items()))), None)

  def add(self, **kwargs):
    itemClass = type(self)
    item = itemClass(**kwargs)
    self.data.append(item)
    return item

class Member(DBList):
  data = []

class Message(DBList):
  data = []

class Bot(DBList):
  data = []

  def set(self, room, name, url):
    return DBList.add(self, room=room, name=name, url=url)

members = Member() 
messages = Message()
bots = Bot()

members.add(id='kenni')
members.add(id='neccsus')
members.add(id='neccsus-bot')

messages.add(author='neccsus', text='Hello, World!')
messages.add(author='kenni', text='Yo!')

bots.set(room='', name='neccsus-bot', url='https://neccsus-bot.herokuapp.com/neccsus/command')
