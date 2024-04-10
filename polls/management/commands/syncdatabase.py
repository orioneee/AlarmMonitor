import json
import os
import time

import requests
import telebot
from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from init_env import init_env
from polls.management.commands.applyapihook import applyApiHook
from polls.models import Region, activeAlarms
from django.contrib.auth.models import User


class Command(BaseCommand):

    def handle(self, *args, **options):
        self.stdout.write("Initing environment")
        init_env()

        self.stdout.write("Chechking is admin user exists")
        if not User.objects.filter(username='admin').exists():
            self.stdout.write("Admin user not found. Creating admin user")
            self.stdout.write("Admin login: " + os.getenv("ADMIN_LOGIN") + " Admin email: " + os.getenv(
                "ADMIN_EMAIL") + " Admin password: " + os.getenv("ADMIN_PASSWORD"))
            User.objects.create_superuser(
                os.getenv("ADMIN_LOGIN"),
                os.getenv("ADMIN_EMAIL"),
                os.getenv("ADMIN_PASSWORD")
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
    api_key = os.getenv('API_TOKEN')
    url = "https://api.ukrainealarm.com/api/v3/regions"
    headers = {
        'Authorization': api_key,
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


def sendMessageToTg(message):
    try:
        token = os.getenv('TG_BOT_TOKEN')
        bot = telebot.TeleBot(token)
        bot.send_message(admin_id, message)
    except Exception as e:
        print(e)


def synchronizeAlarms():
    api_key = os.getenv('API_TOKEN')

    url = "https://api.ukrainealarm.com/api/v3/alerts/"

    headers = {
        'authorization': api_key,
        'Content-Type': 'application/json'
    }

    response = requests.get(url, headers=headers)
    print("Response status code:", response.status_code)
    if response.status_code != 200:
        raise CommandError("Failed to get alerts from API")

    sendMessageToTg(json.dumps(response.json(), indent=4))
    data = response.json()

    sendMessageToTg(json.dumps(data, indent=4))

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
            activeAlarm = activeAlarms(region=regionN, type=alarmType, createdAt=createdAt)
            activeAlarm.save()
