import threading
import time

import requests
import telebot
from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from Secrets import *
from polls.management.commands.applyapihook import applyApiHook
from polls.models import Region, ActiveAlarm
from django.contrib.auth.models import User


class Command(BaseCommand):

    def handle(self, *args, **options):
        self.stdout.write("Initing environment")

        self.stdout.write("Chechking is admin user exists")
        if not User.objects.filter(username='admin').exists():
            self.stdout.write("Admin user not found. Creating admin user")
            User.objects.create_superuser(
                ADMIN_LOGIN,
                ADMIN_EMAIL,
                ADMIN_PASSWORD
            )
            self.stdout.write("Admin user created")
        else:
            self.stdout.write("Admin user already exists")

        self.stdout.write("Synchronizing database")
        self.stdout.write("Loading cities")
        loadCities()
        for i in range(60):
            self.stdout.write(f"Waiting for {60 - i} seconds")
            time.sleep(1)
        synchronizeAlarms()
        for i in range(30):
            self.stdout.write(f"Waiting for {60 - i} seconds")
            time.sleep(1)

        print("Applying webhook")
        applyApiHook()
        self.stdout.write("Database synchronized")


def loadCities():
    url = "https://api.ukrainealarm.com/api/v3/regions"
    headers = {
        'Authorization': API_TOKEN,
        'Content-Type': 'application/json'
    }

    response = requests.get(url, headers=headers)
    print("Response status code:", response.status_code)
    if response.status_code != 200:
        raise CommandError("Failed to get regions from API")
    data = response.json()

    states = data.get('states', [])

    with transaction.atomic():
        Region.objects.all().delete()

        for state in states:
            parent_region = Region.objects.create(
                regionId=state['regionId'],
                regionName=state['regionName'],
                regionType=state['regionType']
            )

            if state.get('regionChildIds'):
                for child1 in state['regionChildIds']:
                    child_region = Region.objects.create(
                        regionId=child1['regionId'],
                        regionName=child1['regionName'],
                        regionType=child1['regionType'],
                        childrenOf=parent_region
                    )

                    if child1.get('regionChildIds'):
                        for child2 in child1['regionChildIds']:
                            Region.objects.create(
                                regionId=child2['regionId'],
                                regionName=child2['regionName'],
                                regionType=child2['regionType'],
                                childrenOf=child_region
                            )
    print("Regions saved successfully")


admin_id = 800918003

def threadSendTelegramMessage(message):
    try:
        bot = telebot.TeleBot(TG_BOT_TOKEN)
        bot.send_message(admin_id, message)
    except Exception as e:
        print(e)

def sendMessageToTg(message):
    thread = threading.Thread(target=threadSendTelegramMessage, args=(message,))
    thread.start()



def synchronizeAlarms():
    url = "https://api.ukrainealarm.com/api/v3/alerts/"

    headers = {
        'authorization': API_TOKEN,
        'Content-Type': 'application/json'
    }

    response = requests.get(url, headers=headers)
    print("Response status code:", response.status_code)
    if response.status_code != 200:
        raise CommandError("Failed to get alerts from API")

    data = response.json()

    with transaction.atomic():

        ActiveAlarm.objects.all().delete()

        for alarm in data:
            regionId = alarm['regionId']

            try:
                regionN = Region.objects.get(regionId=regionId)
            except ObjectDoesNotExist:
                continue

            alerts = alarm["activeAlerts"]

            for alert in alerts:
                regionIdn = alert['regionId']
                alarmType = alert['type']
                createdAt = alert['lastUpdate']

                print("Region:", regionIdn, "Type:", alarmType, "Created at:", createdAt)

                try:
                    regionN = Region.objects.get(regionId=regionIdn)
                except ObjectDoesNotExist:
                    continue
                ActiveAlarm.objects.create(
                    region=regionN,
                    createdAt=createdAt,
                    type=alarmType,
                )
