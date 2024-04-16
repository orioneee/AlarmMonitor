import datetime
import os
import threading

import requests
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.shortcuts import render

# Create your views here.

from django.http import JsonResponse, HttpResponse
import json

from django.views.decorators.csrf import csrf_exempt
from firebase_admin import messaging

from polls.alarmMapJenerator import generateMap, sendMessageToTg
from polls.management.commands.applyapihook import applyApiHook
from polls.management.commands.syncdatabase import loadCities, synchronizeAlarms
from polls.models import Region, ActiveAlarm, UserFcmToken
import geopandas as gpd
vinnitsiaId = 155


def index(request):
    return JsonResponse({'foo': 'bar'}, status=200)


@csrf_exempt
def registerFcmToken(request):
    body = request.body.decode('utf-8')
    data = json.loads(body)
    fcmToken = data.get('fcmToken')
    user_id = data.get('user_id')

    # check if token already exists
    fcmTokenObj = UserFcmToken.objects.filter(fcmToken=fcmToken).first()
    if fcmTokenObj:
        return JsonResponse({'status': 'Token already exists'}, status=200)
    expiredAt = datetime.datetime.now() + datetime.timedelta(days=60)
    fcmTokenObj = UserFcmToken(user_id=user_id, fcmToken=fcmToken, expiredAt=expiredAt)

    fcmTokenObj.save()

    return JsonResponse({'status': 'ok'}, status=200)


def fullAlarms(request):
    states = Region.objects.filter(regionType="State").all()
    with transaction.atomic():
        for state in states:
            ActiveAlarm.objects.create(
                    region=state,
                    createdAt=datetime.datetime.now(),
                    type="AIR"
                )

    return JsonResponse({'status': 'ok'}, status=200)


def hasActiveAlrmInRegion(region: Region):
    alarms = ActiveAlarm.objects.filter(region=region).all()
    if len(alarms) > 0:
        return True
    if region.childrenOf and region.childrenOf != region:
        return hasActiveAlrmInRegion(region.childrenOf)
    return False


def hasActiveAlarms(request, regionId):
    try:
        region = Region.objects.get(regionId=regionId)
    except ObjectDoesNotExist:
        return JsonResponse({'error': 'Region not found'}, status=400)

    return JsonResponse({'hasActiveAlarm': hasActiveAlrmInRegion(region)}, status=200)


def applyAlarmHook(request):
    r = applyApiHook()
    return JsonResponse(
        {
            "status": r.status_code == 200,
            "status_code": r.status_code,
            "response": r.text
        },
        status=r.status_code
    )


@csrf_exempt
def hook(request):
    body = request.body.decode('utf-8')
    data = json.loads(body)
    sendMessageToTg(json.dumps(data, indent=4))
    return JsonResponse({'status': 'ok'}, status=200)


def threadPushNewAlarm(time: str):
    fcmTokens = UserFcmToken.objects.all()
    registration_ids = [token.fcmToken for token in fcmTokens]
    print(registration_ids)
    message = messaging.MulticastMessage(
        data={
            "type": "alarm",
            "isStarting": "1",
            "time": time,
        },
        tokens=registration_ids,
    )
    resp = messaging.send_each_for_multicast(message)
    for r in resp.responses:
        print(r.exception)


def pushNewAlarm(time: str):
    print("Pushing new alarm")
    thread = threading.Thread(target=threadPushNewAlarm, args=(datatimeToTimeStr(time),))
    thread.start()


def threadPushFinishAlarm(time: str):
    fcmTokens = UserFcmToken.objects.all()
    registration_ids = [token.fcmToken for token in fcmTokens]
    print(registration_ids)
    message = messaging.MulticastMessage(
        data={
            "type": "alarm",
            "isStarting": "0",
            "time": time,
        },
        tokens=registration_ids,
    )
    resp = messaging.send_each_for_multicast(message)
    for r in resp.responses:
        print(r.exception)


def pushFinishAlarm(time: str):
    print("Pushing finish alarm")
    thread = threading.Thread(target=threadPushFinishAlarm, args=(datatimeToTimeStr(time),))
    thread.start()


def datatimeToTimeStr(dt: str):
    dt_obj = datetime.datetime.strptime(dt, '%Y-%m-%dT%H:%M:%SZ')
    time_str = dt_obj.strftime('%H:%M:%S')
    return time_str


def isChild(region: Region, parent: Region):
    if region == parent:
        return True
    if not region.childrenOf:
        return False
    if region.childrenOf == parent:
        return True
    return isChild(region.childrenOf, parent)


def genMap(request):
    threading.Thread(target=generateMap).start()

    return JsonResponse({'status': 'ok'}, status=200)


def getAlarmMap(request):
    image_path = "alarm_map.png"
    if not os.path.exists(image_path):
        return JsonResponse({'error': 'Map not generated yet'}, status=400)

    with open(image_path, 'rb') as image_file:
        image_data = image_file.read()

    return HttpResponse(image_data, content_type='image/png')


@csrf_exempt
def alarmHook(request):
    try:
        body = request.body.decode('utf-8')
        data = json.loads(body)
        status = data.get('status')
        regionId = data.get('regionId')
        alarmType = data.get('alarmType')
        createdAt = data.get('createdAt')

        try:
            region = Region.objects.filter(regionId=regionId).first()
            vinnitsiaRegion = Region.objects.filter(regionId=vinnitsiaId).first()
        except ObjectDoesNotExist:
            return JsonResponse({'error': 'Region not found'}, status=200)

        sendMessageToTg("In region: " + region.regionName + " alarm is " + (
            "activated" if status == "Activate" else "deactivated") + " type: " + alarmType)

        print("Is child:", isChild(vinnitsiaRegion, region))

        if status == "Activate":
            if isChild(vinnitsiaRegion, region):
                pushNewAlarm(createdAt)

            alarm = ActiveAlarm(region=region, type=alarmType, createdAt=createdAt)
            alarm.save()
        else:
            try:
                if isChild(vinnitsiaRegion, region):
                    pushFinishAlarm(createdAt)

                alarms = ActiveAlarm.objects.filter(region=region).all()
                for alarm in alarms:
                    alarm.delete()
            except ObjectDoesNotExist:
                return JsonResponse({'error': 'Alarm not found'}, status=200)

        threading.Thread(target=generateMap).start()
        return JsonResponse({'status': 'ok'}, status=200)
    except Exception as e:
        return JsonResponse({
            'status': 'ok',
            'error': str(e)
        }, status=200)


def syncCities(request):
    try:
        loadCities()
        return JsonResponse({'status': 'ok'}, status=200)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


def syncAlarms(request):
    try:
        synchronizeAlarms()
        return JsonResponse({'status': 'ok'}, status=200)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


def static(request, path):
    return render(request, path)
