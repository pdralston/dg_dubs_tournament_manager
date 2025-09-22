from web_app.app import app

# Elastic Beanstalk expects the WSGI application to be named 'application'
application = app

if __name__ == "__main__":
    application.run(debug=True)
