import os

import requests
from django.core.management import BaseCommand

from Secrets import API_TOKEN


class Command(BaseCommand):

    def handle(self, *args, **options):
        applyApiHook()


def applyApiHook():
    body = {
        "webHookUrl": "https://alarm-monitor.onrender.com/alarmHook/"
    }
    url = "https://api.ukrainealarm.com/api/v3/webhook"
    headers = {
        'authorization': API_TOKEN,
        'Content-Type': 'application/json'
    }
    r = requests.post(url, json=body, headers=headers)
    print("Is applyApiHook successfull: ", r.status_code == 200, "status code: ", r.status_code)
    return r
