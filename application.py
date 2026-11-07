from backend.app import create_app, socketio

# Elastic Beanstalk expects the WSGI application to be named 'application'.
application = create_app()

if __name__ == "__main__":
    # socketio.run serves both HTTP routes and the WebSocket transport used by
    # DG-Putt's live bracket/match updates.
    socketio.run(application, debug=True)
