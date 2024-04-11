import datetime
import os
import threading

import requests
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import render

# Create your views here.

from django.http import JsonResponse
import json

from django.views.decorators.csrf import csrf_exempt
from firebase_admin import messaging

from polls.management.commands.applyapihook import applyApiHook
from polls.management.commands.syncdatabase import loadCities, synchronizeAlarms, sendMessageToTg
from polls.models import Region, ActiveAlarm, UserFcmToken

vinnitsiaId = 4


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


def hasActiveAlarms(request, regionId):
    try:
        region = Region.objects.get(regionId=regionId)
    except ObjectDoesNotExist:
        return JsonResponse({'error': 'Region not found'}, status=400)

    alarms = ActiveAlarm.objects.filter(region=region).all()
    if alarms:
        return JsonResponse({'hasActiveAlarms': True}, status=200)
    else:
        return JsonResponse({'hasActiveAlarms': False}, status=200)


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
    thread = threading.Thread(target=threadPushFinishAlarm, args=(datatimeToTimeStr(time),))
    thread.start()


def datatimeToTimeStr(dt: str):
    dt_obj = datetime.datetime.strptime(dt, '%Y-%m-%dT%H:%M:%SZ')
    time_str = dt_obj.strftime('%H:%M:%S')
    return time_str


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
        except ObjectDoesNotExist:
            return JsonResponse({'error': 'Region not found'}, status=200)

        if status == "Activate":
            alarm = ActiveAlarm(region=region, type=alarmType, createdAt=createdAt)
            alarm.save()

            if regionId == vinnitsiaId:
                sendMessageToTg(f"Alarm in Vinnitsia: {alarmType}")
                pushNewAlarm(createdAt)

        else:
            try:
                alarms = ActiveAlarm.objects.filter(region=region).all()
                if regionId == vinnitsiaId:
                    sendMessageToTg(f"Alarm in Vinnitsia: {alarmType} is over")
                    pushFinishAlarm(createdAt)

                for alarm in alarms:
                    alarm.delete()
            except ObjectDoesNotExist:
                return JsonResponse({'error': 'Alarm not found'}, status=200)

        sendMessageToTg(json.dumps(data, indent=4))
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
