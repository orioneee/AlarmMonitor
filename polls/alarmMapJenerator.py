import os
import threading
import time

import geopandas as gpd
import matplotlib.pyplot as plt
import telebot

from Secrets import TG_BOT_TOKEN
from polls.models import Region, ActiveAlarm


def generateMap(states_layer):
    print("Generating map")

    states = Region.objects.filter(regionType="State")

    activeAlarms = ActiveAlarm.objects.all()

    activeAlarmsStatesIds = []

    for state in states:
        if activeAlarms.filter(region=state).exists():
            activeAlarmsStatesIds.append(state.regionId)

    print("Active alarms states ids:", activeAlarmsStatesIds)

    create_alarm_map(activeAlarmsStatesIds, states_layer)

    print("Map generated")


def create_alarm_map(active_alarm_ids, states_layer):
    message = ""

    start_reading_time = time.time()

    message += "Reading shapefile time: " + str(time.time() - start_reading_time) + "\n"
    start_plotting_time = time.time()
    name_to_id = {
        3: "Хмельницька",
        4: "Вінницька",
        5: "Рівненська",
        8: "Волинська",
        9: "Дніпропетровська",
        10: "Житомирська",
        11: "Закарпатська",
        12: "Запорізька",
        13: "Івано-Франківська",
        14: "Київська",
        15: "Кіровоградська",
        16: "Луганська",
        17: "Миколаївська",
        18: "Одеська",
        19: "Полтавська",
        20: "Сумська",
        21: "Тернопільська",
        22: "Харківська",
        23: "Херсонська",
        24: "Черкаська",
        25: "Чернігівська",
        26: "Чернівецька",
        27: "Львівська",
        28: "Донецька",
        31: "Київ",
        9999: "Автономна Республіка Крим",
    }

    admin_names = [name_to_id[id] for id in active_alarm_ids]
    alarmed_states = states_layer[states_layer['ADM1_UA'].isin(admin_names)]

    default_color = "#5D6D7E"
    alarm_color = "#E74C3C"

    fig, ax = plt.subplots(figsize=(10, 10), dpi=150)
    ax.set_axis_off()

    states_layer.plot(ax=ax, linewidth=0.3, color=default_color, legend=False, edgecolor='black')

    alarmed_states.plot(ax=ax, linewidth=0.3, color=alarm_color, legend=False, edgecolor='black')

    output_path = "alarm_map.png"
    plt.savefig(output_path, bbox_inches='tight', pad_inches=0.1)
    plt.close()

    message += "Plotting time: " + str(time.time() - start_plotting_time) + "\n"

    print("Sending to telegram")

    sendAlarmMapToTg(message)

    print("Sent to telegram")


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
