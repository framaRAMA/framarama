# Generated by Django 4.0.10 on 2023-11-13 16:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('config', '0029_alter_source_update_interval'),
    ]

    operations = [
        migrations.AddField(
            model_name='displaystatus',
            name='app_checked',
            field=models.DateTimeField(blank=True, help_text='Date of last update check', null=True, verbose_name='Application update check'),
        ),
        migrations.AddField(
            model_name='displaystatus',
            name='app_installed',
            field=models.DateTimeField(blank=True, help_text='Date of last update installation', null=True, verbose_name='Application installation'),
        ),
    ]