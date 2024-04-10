import os

import requests
from django.core.management import BaseCommand


class Command(BaseCommand):

    def handle(self, *args, **options):
        applyApiHook()


def applyApiHook():
    body = {
        "webHookUrl": "https://alarmmonitor.onrender.com/alarmHook/"
    }
    api_key = os.getenv('API_TOKEN')
    url = "https://api.ukrainealarm.com/api/v3/webhook"
    headers = {
        'authorization': api_key,
        'Content-Type': 'application/json'
    }
    r = requests.post(url, json=body, headers=headers)
    print("Is applyApiHook successfull: ", r.status_code == 200, "status code: ", r.status_code)
    return r
