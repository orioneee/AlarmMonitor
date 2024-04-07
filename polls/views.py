import requests
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import render

# Create your views here.

from django.http import HttpResponse, JsonResponse
import telebot
import json

from django.views.decorators.csrf import csrf_exempt
from firebase_admin import messaging

from polls.models import Token, Region, activeAlarms, userFcmToken

admin_id = 800918003

vinnitsiaId = 4


def index(request):
    return JsonResponse({'foo': 'bar'}, status=200)


def hasActiveAlarms(request, regionId):
    try:
        region = Region.objects.get(regionId=regionId)
    except ObjectDoesNotExist:
        return JsonResponse({'error': 'Region not found'}, status=400)

    alarms = activeAlarms.objects.filter(region=region).all()
    if alarms:
        return JsonResponse({'hasActiveAlarms': True}, status=200)
    else:
        return JsonResponse({'hasActiveAlarms': False}, status=200)


def sendMessageToTg(message):
    token = Token.objects.get(type='bot').token
    bot = telebot.TeleBot(token)
    bot.send_message(admin_id, message)


@csrf_exempt
def hook(request):
    body = request.body.decode('utf-8')
    data = json.loads(body)
    sendMessageToTg(json.dumps(data, indent=4))
    return JsonResponse({'status': 'ok'}, status=200)


def pushNewAlarm():
    fcmTokens = userFcmToken.objects.all()
    registration_ids = [token.fcmToken for token in fcmTokens]
    print(registration_ids)
    message = messaging.MulticastMessage(
        data={
            "type": "alarm",
            "isStarting": "1",
        },
        tokens=registration_ids,
    )
    resp = messaging.send_each_for_multicast(message)
    for r in resp.responses:
        print(r.exception)


def pushFinishAlarm():
    fcmTokens = userFcmToken.objects.all()
    registration_ids = [token.fcmToken for token in fcmTokens]
    print(registration_ids)
    message = messaging.MulticastMessage(
        data={
            "type": "alarm",
            "isStarting": "1",
        },
        tokens=registration_ids,
    )
    resp = messaging.send_each_for_multicast(message)
    for r in resp.responses:
        print(r.exception)


@csrf_exempt
def alarmHook(request):
    body = request.body.decode('utf-8')
    data = json.loads(body)
    status = data.get('status')
    regionId = data.get('regionId')
    alarmType = data.get('alarmType')
    createdAt = data.get('createdAt')

    try:
        region = Region.objects.filter(regionId=regionId).first()
    except ObjectDoesNotExist:
        return JsonResponse({'error': 'Region not found'}, status=200)

    if status == "Activate":
        alarm = activeAlarms(region=region, type=alarmType, createdAt=createdAt)
        alarm.save()

        if regionId == vinnitsiaId:
            sendMessageToTg(f"Alarm in Vinnitsia: {alarmType}")
            pushNewAlarm()

    else:
        try:
            alarms = activeAlarms.objects.filter(region=region).all()
            if regionId == vinnitsiaId:
                sendMessageToTg(f"Alarm in Vinnitsia: {alarmType} is over")
                pushFinishAlarm()

            for alarm in alarms:
                alarm.delete()
        except ObjectDoesNotExist:
            return JsonResponse({'error': 'Alarm not found'}, status=200)

    return JsonResponse({'status': 'ok'}, status=200)


def loadCities(request):
    try:
        api_key = Token.objects.get(type='api').token
    except Token.DoesNotExist:
        return JsonResponse({'error': 'API token not found'}, status=400)

    url = "https://api.ukrainealarm.com/api/v3/regions"
    headers = {
        'Authorization': api_key,
        'Content-Type': 'application/json'
    }

    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        return JsonResponse({
            "error": "Failed to get regions from API",
            "response": response.text
        }, status=response.status_code)
    data = response.json()

    states = data.get('states', [])
    Region.objects.all().delete()

    for state in states:
        regionId = state['regionId']
        regionName = state['regionName']
        regionType = state['regionType']

        parent_region = Region(regionId=regionId, regionName=regionName, regionType=regionType)
        parent_region.save()

        if state.get('regionChildIds'):
            for child1 in state['regionChildIds']:
                childId = child1['regionId']
                childName = child1['regionName']
                childType = child1['regionType']

                child_region = Region(regionId=childId, regionName=childName, regionType=childType,
                                      childrenOf=parent_region)
                child_region.save()

                if child1.get('regionChildIds'):
                    for child2 in child1['regionChildIds']:
                        childId = child2['regionId']
                        childName = child2['regionName']
                        childType = child2['regionType']

                        # Create the grandchild Region object with parent reference
                        grandchild_region = Region(regionId=childId, regionName=childName, regionType=childType,
                                                   childrenOf=child_region)
                        grandchild_region.save()

    return JsonResponse({'status': 'ok'}, status=200)


def synchronizeAlarms(request):
    api_key = Token.objects.get(type='api').token

    url = "https://api.ukrainealarm.com/api/v3/alerts/"

    headers = {
        'Authorization': api_key,
        'Content-Type': 'application/json'
    }

    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        return JsonResponse({
            "error": "Failed to get alarms from API",
            "response": response.text
        }, status=response.status_code)

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

            try:
                regionN = Region.objects.get(regionId=regionIdn)
            except ObjectDoesNotExist:
                continue
            activeAlarm = activeAlarms(region=regionN, type=alarmType, createdAt=createdAt)
            activeAlarm.save()

    return JsonResponse({'status': 'ok'}, status=200)


def static(request, path):
    return render(request, path)
