import os
import threading

import geopandas as gpd
import matplotlib.pyplot as plt
import telebot

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
    states_shapefile = "states/ukr_admbnda_adm1_sspe_20230201.shp"
    states_layer = gpd.read_file(states_shapefile, encoding='utf-8')
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

    default_color = "#5D6D7E"
    alarm_color = "#E74C3C"

    fig, ax = plt.subplots(figsize=(10, 10), dpi=150)
    ax.set_axis_off()

    states_layer.plot(ax=ax, linewidth=0.3, color=default_color, legend=False, edgecolor='black')

    for name in admin_names:
        states_layer.loc[states_layer['ADM1_UA'] == name].plot(ax=ax, linewidth=0.3, edgecolor='black',
                                                               color=alarm_color, legend=False)

    output_path = "alarm_map.png"
    plt.savefig(output_path, bbox_inches='tight', pad_inches=0.1)

    plt.close()

    print("Sending to telegram")

    sendAlarmMapToTg()

    print("Sent to telegram")

def sendAlarmMapToTg():
    admin_id = 800918003

    bot = telebot.TeleBot(TG_BOT_TOKEN)

    if os.path.exists("alarm_map.png"):
        with open('alarm_map.png', 'rb') as photo:
            bot.send_photo(admin_id, photo)

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