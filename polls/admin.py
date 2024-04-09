from django.contrib import admin

# Register your models here.

from .models import Region, activeAlarms, userFcmToken


class RegionAdmin(admin.ModelAdmin):
    list_display = ('regionId', 'regionName', 'regionType', 'childrenOf')
    list_filter = ('regionType', "childrenOf")


class activeAlarmsAdmin(admin.ModelAdmin):
    list_display = ('id', 'region', 'createdAt', 'type')

class userFcmTokenAdmin(admin.ModelAdmin):
    list_display = ('user_id', 'fcmToken', 'expiredAt')


admin.site.register(Region, RegionAdmin)
admin.site.register(activeAlarms, activeAlarmsAdmin)
admin.site.register(userFcmToken, userFcmTokenAdmin)
