from necsus import app, init_db

import api
import frontend

if __name__ == '__main__':
  init_db()
  app.run(debug=True, port=5005)
