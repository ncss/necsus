from .server import app

if __name__ == '__main__':
    app.run(port=1234, debug=True)
