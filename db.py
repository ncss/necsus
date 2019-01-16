import sqlite3

class DBList(dict):
  data = []

  def list(self):
    return self.data

  def find(self, id):
    return next(item for item in self.data if item.get('id') == id)

  def add(self, **kwargs):
    itemClass = type(self)
    item = itemClass(**kwargs)
    self.data.append(item)
    return item

class Member(DBList):
  data = []

class Message(DBList):
  data = []

class Endpoint():
  interactivity_url = None
  command_urls = {}

  def set(self, url, endpoint='command', command=None):
    if endpoint == 'command':
      if not command:
        raise KeyError('Not sure which command this url is for.')
      else:
        self.command_urls[command] = url
        return url
    elif endpoint == 'interactivity':
      self.interectivity_url = url 
      return url

  def find(self, endpoint='command', command=None): 
    if endpoint == 'command':
      if command:
        return self.command_urls.get(command)
      else:
        return self.command_urls
    elif endpoint == 'interactivity':
      return self.interectivity_url

members = Member() 
messages = Message()
endpoints = Endpoint()

members.add(id='kenni')
members.add(id='neccsus')
members.add(id='neccsus-bot')

messages.add(author='necssus', text='Hello, World!')
messages.add(author='kenni', text='Yo!')

endpoints.set(url='http://localhost:5000/neccsus/command', endpoint='command', command='neccsus-bot')
endpoints.set(url='http://localhost:5000/neccsus/interactivity', endpoint='interactivity')
