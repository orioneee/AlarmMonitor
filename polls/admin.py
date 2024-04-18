from django.contrib import admin

# Register your models here.

from .models import Region, ActiveAlarm, UserFcmToken


class RegionAdmin(admin.ModelAdmin):
    list_display = ('regionId', 'regionName', 'regionType', 'childrenOf')
    list_filter = ('regionType', "childrenOf")

    ordering = ('regionId',)


class activeAlarmsAdmin(admin.ModelAdmin):
    list_display = ('id', 'region', 'createdAt', 'type')

    ordering = ('-createdAt',)


class userFcmTokenAdmin(admin.ModelAdmin):
    list_display = ('user_login', 'fcmToken', 'device_name', 'os_name', 'device_android_sdk', 'app_version_code',
                    'device_model', 'expiredAt')

    list_filter = ('user_login', 'device_name', 'os_name', 'device_android_sdk', 'app_version_code', 'device_model',
                   'expiredAt')
    ordering = ('-expiredAt',)


admin.site.register(Region, RegionAdmin)
admin.site.register(ActiveAlarm, activeAlarmsAdmin)
admin.site.register(UserFcmToken, userFcmTokenAdmin)
