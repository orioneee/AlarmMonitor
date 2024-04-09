from django.db import models



alarmTypes = (
    ('State', 'State'),
    ('District', 'District'),
    ("Community", "Community"),
    ("none", None)
)


class Region(models.Model):
    regionId = models.IntegerField()
    regionName = models.CharField(max_length=100)
    regionType = models.CharField(max_length=100, choices=alarmTypes)
    childrenOf = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return self.regionName


class activeAlarms(models.Model):
    types = (
        ("UNKNOWN", "UNKNOWN"),
        ("AIR", "AIR"),
        ("ARTILLERY", "ARTILLERY"),
        ("URBAN_FIGHTS", "URBAN_FIGHTS"),
        ("CHEMICAL", "CHEMICAL"),
        ("NUCLEAR", "NUCLEAR"),
        ("INFO", "INFO")
    )
    id = models.IntegerField(primary_key=True, auto_created=True)
    region = models.ForeignKey(Region, on_delete=models.CASCADE)
    createdAt = models.DateTimeField()
    type = models.CharField(max_length=100, choices=types)


class userFcmToken(models.Model):
    user_id = models.IntegerField()
    fcmToken = models.CharField(max_length=500)
    expiredAt = models.DateTimeField()
