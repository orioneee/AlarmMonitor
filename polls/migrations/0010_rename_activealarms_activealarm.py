# Generated by Django 5.0.4 on 2024-04-09 18:11

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('polls', '0009_delete_token'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='activeAlarms',
            new_name='ActiveAlarm',
        ),
    ]
