from flask import Flask
from app.routes.routes import main
import firebase_admin
from firebase_admin import credentials
import os

from flask import Flask
from app.routes.routes import main
import firebase_admin
from firebase_admin import credentials
import os

def create_app():
    app = Flask(__name__)

    app.secret_key = "retinascan-secret-2024"
    app.config['UPLOAD_FOLDER'] = 'app/static/uploads'

    if not firebase_admin._apps:
        cred = credentials.Certificate(
            os.path.join(os.path.dirname(__file__), '..', 'serviceAccountKey.json')
        )
        firebase_admin.initialize_app(cred)

    app.register_blueprint(main)
    return app