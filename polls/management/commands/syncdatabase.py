import json
import os
import time

import requests
import telebot
from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import BaseCommand, CommandError

from init_env import init_env
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
    Region.objects.all().delete()

    for state in states:
        regionId = state['regionId']
        regionName = state['regionName']
        regionType = state['regionType']

        print("Parent region:", regionId, regionName, regionType)

        parent_region = Region(regionId=regionId, regionName=regionName, regionType=regionType)
        parent_region.save()

        if state.get('regionChildIds'):
            for child1 in state['regionChildIds']:
                childId = child1['regionId']
                childName = child1['regionName']
                childType = child1['regionType']

                print("Child region:", childId, childName, childType)

                child_region = Region(regionId=childId, regionName=childName, regionType=childType,
                                      childrenOf=parent_region)
                child_region.save()

                if child1.get('regionChildIds'):
                    for child2 in child1['regionChildIds']:
                        childId = child2['regionId']
                        childName = child2['regionName']
                        childType = child2['regionType']

                        print("Grandchild region:", childId, childName, childType)

                        grandchild_region = Region(regionId=childId, regionName=childName, regionType=childType,
                                                   childrenOf=child_region)
                        grandchild_region.save()


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
