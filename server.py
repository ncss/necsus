from necsus import app, init_db

# Importing these for effect (they add routes to the app)
import api
import frontend

if __name__ == '__main__':
  init_db()
  app.run(host="0.0.0.0", port=6277)
