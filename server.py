from necsus import app

# Importing these for effect (they add routes to the app)
import api
import frontend
import ws

if __name__ == '__main__':
  app.run(host="0.0.0.0", port=6277)
