import datetime
import os
import threading
import zipfile

from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
import json
from django.views.decorators.csrf import csrf_exempt
from firebase_admin import messaging
from polls.alarmMapJenerator import generateMap, sendMessageToTg, sendFileToTg
from polls.management.commands.applyapihook import applyApiHook
from polls.management.commands.syncdatabase import loadCities, synchronizeAlarms
from polls.models import Region, ActiveAlarm, UserFcmToken

vinParrents = [4, 36, 155]


def index(request):
    return JsonResponse({'foo': 'bar'}, status=200)


@csrf_exempt
def registerFcmToken(request):
    try:
        body = request.body.decode('utf-8')
        data = json.loads(body)
        login = data.get('login')
        fcmToken = data.get('fcmToken')

        headers = request.headers
        device_brand = headers.get('Device-Brand', "")
        device_name = headers.get('Device-Name', "")
        device_os = headers.get('Device-OS', "")
        device_sdk = headers.get('Device-SDK-Version', 0)
        device_model = headers.get('Device-Model', "")
        app_version_code = headers.get('App-Version-Code', 0)

        if not login or not fcmToken:
            return JsonResponse({'error': 'login and fcmToken required'}, status=400)

        if UserFcmToken.objects.filter(fcmToken=fcmToken).exists():
            return JsonResponse({'status': 'token already exists'}, status=200)

        UserFcmToken.objects.create(
            user_login=login,
            fcmToken=fcmToken,
            device_name=device_name,
            os_name=device_os,
            device_android_sdk=device_sdk,
            app_version_code=app_version_code,
            device_model=device_brand + " " + device_model,
            expiredAt=datetime.datetime.now() + datetime.timedelta(days=60)
        )

        return JsonResponse({'status': 'ok'}, status=200)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


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


def getAllDistrict(request):
    districts = Region.objects.filter(regionType="District").all()
    result = []
    for district in districts:
        result.append({
            "regionId": district.regionId,
            "regionName": district.regionName
        })

    return JsonResponse({'districts': result}, status=200)


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


def pushNewAlarm(time: str):
    fcmTokens = UserFcmToken.objects.all()
    if not fcmTokens or len(fcmTokens) == 0:
        return
    registration_ids = [token.fcmToken for token in fcmTokens]
    print(registration_ids)
    message = messaging.MulticastMessage(
        data={
            "type": "alarm",
            "isStarting": "1",
            "time": datatimeToTimeStr(time),
        },
        tokens=registration_ids,
    )
    resp = messaging.send_each_for_multicast(message)
    for r in resp.responses:
        print(r.exception)


def pushFinishAlarm(time: str):
    fcmTokens = UserFcmToken.objects.all()
    if not fcmTokens or len(fcmTokens) == 0:
        return
    registration_ids = [token.fcmToken for token in fcmTokens]
    print(registration_ids)
    message = messaging.MulticastMessage(
        data={
            "type": "alarm",
            "isStarting": "0",
            "time": datatimeToTimeStr(time),
        },
        tokens=registration_ids,
    )
    resp = messaging.send_each_for_multicast(message)
    for r in resp.responses:
        print(r.exception)


def regionToJson(region: Region):
    return {
        "regionId": region.regionId,
        "regionName": region.regionName,
        "regionType": region.regionType,
        "childrenOf": regionToJson(region.childrenOf) if region.childrenOf else None
    }


def alarmToJson(alarm: ActiveAlarm):
    return {
        "id": alarm.id,
        "region": regionToJson(alarm.region),
        "createdAt": alarm.createdAt,
        "type": alarm.type
    }


def tokenToJson(token: UserFcmToken):
    return {
        "id": token.id,
        "user_login": token.user_login,
        "fcmToken": token.fcmToken,
        "device_name": token.device_name,
        "os_name": token.os_name,
        "device_android_sdk": token.device_android_sdk,
        "app_version_code": token.app_version_code,
        "device_model": token.device_model,
        "expiredAt": token.expiredAt.strftime("%Y-%m-%d %H:%M:%S")
    }


def makeDbBackup(request):
    print("Making backup")
    # regions = Region.objects.all()
    # alarms = ActiveAlarm.objects.all()
    tokens = UserFcmToken.objects.all()

    current_time = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    # with open(f"backup_regions.json", "w") as f:
    #     json.dump([regionToJson(region) for region in regions], f, indent=4)
    #
    # with open(f"backup_alarms.json", "w") as f:
    #     json.dump([alarmToJson(alarm) for alarm in alarms], f, indent=4)

    data = [tokenToJson(token) for token in tokens]
    print(data)
    with open(f"backup_tokens.json", "w") as f:
        f.write(json.dumps({
            "tokens": data,
        }, indent=4))

    files_to_add = [
        #     "backup_regions.json",
        #     "backup_alarms.json",
        "backup_tokens.json"
    ]

    with zipfile.ZipFile(f"db_backup_{current_time}.zip", 'w') as zipf:
        for file_path in files_to_add:
            file_name = os.path.basename(file_path)
            zipf.write(file_path, arcname=file_name)

    sendFileToTg(f"db_backup_{current_time}.zip", "Database backup")

    # os.remove("backup_regions.json")
    # os.remove("backup_alarms.json")
    try:
        os.remove("backup_tokens.json")
        os.remove(f"db_backup_{current_time}.zip")
    except Exception as e:
        print(e)

    return JsonResponse({'status': 'ok'}, status=200)


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


def isVinnitsiaParent(regionId: str):
    return regionId in vinParrents


def alarmHook(request):
    try:
        body = request.body.decode('utf-8')
        data = json.loads(body)
        status = data.get('status')
        regionId = data.get('regionId')
        alarmType = data.get('alarmType')
        createdAt = data.get('createdAt')

        if regionId not in vinParrents:
            return JsonResponse({'status': 'ignoring'}, status=200)

        if status == "Activate" and isVinnitsiaParent(regionId):
            pushNewAlarm(createdAt)
        elif isVinnitsiaParent(regionId):
            pushFinishAlarm(createdAt)

        try:
            region = Region.objects.filter(regionId=regionId).first()
        except ObjectDoesNotExist:
            return JsonResponse({'error': 'Region not found'}, status=200)

        sendMessageToTg("In region: " + region.regionName + " alarm is " + (
            "activated" if status == "Activate" else "deactivated") + " type: " + alarmType)

        if status == "Activate":
            alarm = ActiveAlarm(region=region, type=alarmType, createdAt=createdAt)
            alarm.save()
        else:
            try:
                alarms = ActiveAlarm.objects.filter(region=region).all()
                for alarm in alarms:
                    alarm.delete()
            except ObjectDoesNotExist:
                return JsonResponse({'error': 'Alarm not found'}, status=200)

        threading.Thread(target=generateMap).start()
        return JsonResponse({'status': 'ok'}, status=200)
    except Exception as e:
        return JsonResponse({"status": "error", "error": str(e)}, status=200)


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
