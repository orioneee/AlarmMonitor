import os
import threading
import time

import geopandas as gpd
import matplotlib.pyplot as plt
import telebot
from PIL import Image

from Secrets import TG_BOT_TOKEN
from polls.models import Region, ActiveAlarm


def generateMap():
    print("Generating map")

    states = Region.objects.filter(regionType="State")

    activeAlarms = ActiveAlarm.objects.all()

    activeAlarmsStatesIds = []

    for state in states:
        if activeAlarms.filter(region=state).exists():
            activeAlarmsStatesIds.append(state.regionId)

    print("Active alarms states ids:", activeAlarmsStatesIds)

    create_alarm_map(activeAlarmsStatesIds)

    print("Map generated")


def create_alarm_map(active_alarm_ids):
    start_time = time.time()

    background = Image.open("masks/background.png").convert("RGBA")

    for alarmId in active_alarm_ids:
        print("Adding alarm", alarmId)
        mask = Image.open(f"masks/{alarmId}.png").convert("RGBA")
        mask = mask.resize(background.size, resample=Image.BILINEAR)
        background.paste(mask, (0, 0), mask)

    background.save("alarm_map.png", "PNG")

    print("Map with alarms generated")

    timing = time.time() - start_time

    sendAlarmMapToTg(f"Map generated in {timing} seconds")


def sendAlarmMapToTg(message: str = ""):
    admin_id = 800918003

    bot = telebot.TeleBot(TG_BOT_TOKEN)

    if os.path.exists("alarm_map.png"):
        with open('alarm_map.png', 'rb') as photo:
            bot.send_photo(admin_id, photo, caption=message)

    else:
        bot.send_message(admin_id, "Map not generated yet")


def sendMessageToTg(message):
    thread = threading.Thread(target=threadSendTelegramMessage, args=(message,))
    thread.start()


def threadSendTelegramMessage(message):
    try:
        admin_id = 800918003
        bot = telebot.TeleBot(TG_BOT_TOKEN)
        bot.send_message(admin_id, message)
    except Exception as e:
        print(e)
