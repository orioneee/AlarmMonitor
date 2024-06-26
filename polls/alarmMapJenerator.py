import os
import threading
import time

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
        try:
            print("Adding alarm", alarmId)
            mask = Image.open(f"masks/{alarmId}.png").convert("RGBA")
            if mask.size != background.size:
                mask = mask.resize(background.size, resample=Image.BILINEAR)
                mask.save(f"masks/{alarmId}.png")
            background.paste(mask, (0, 0), mask)
        except Exception as e:
            sendMessageToTg(f"Error while adding alarm {alarmId} to map: {e}")

    background.save("alarm_map.png", "PNG")

    print("Map with alarms generated")

    timing = time.time() - start_time

    sendAlarmMapToTg(f"Map generated in {timing} seconds")


def sendAlarmMapToTg(message: str = ""):
    sendFileToTg("alarm_map.png", message)

def sendFileToTg(file_path: str, message: str = ""):
    admin_id = 800918003

    bot = telebot.TeleBot(TG_BOT_TOKEN)

    if os.path.exists(file_path):
        with open(file_path, 'rb') as file:
            if file_path.endswith(".png"):
                bot.send_photo(admin_id, file, caption=message)
            else:
                bot.send_document(admin_id, file, caption=message)

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
