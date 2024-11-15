# Generated by Django 4.0.10 on 2023-11-22 15:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('config', '0030_displaystatus_app_checked_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='displaystatus',
            name='app_uptime',
            field=models.BigIntegerField(blank=True, help_text='The uptime of the application in seconds', null=True, verbose_name='Application uptime'),
        ),
        migrations.AlterField(
            model_name='displaystatus',
            name='uptime',
            field=models.BigIntegerField(blank=True, help_text='The uptime of the device in seconds', null=True, verbose_name='Uptime'),
        ),
    ]
