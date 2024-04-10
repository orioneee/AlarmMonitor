from django.apps import AppConfig
import firebase_admin
from firebase_admin import credentials



class FirebaseUtilsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'firebase_utils'

    def ready(self):
        cred = credentials.Certificate("key.json")
        firebase_admin.initialize_app(cred)
