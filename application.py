from backend.app import create_app

# Elastic Beanstalk expects the WSGI application to be named 'application'
application = create_app()

if __name__ == "__main__":
    application.run(debug=True)
