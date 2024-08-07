# Generated by Django 4.0.10 on 2023-11-15 17:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('frontend', '0013_config_app_update_check_date_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='config',
            name='app_update_check_status',
            field=models.CharField(help_text='Status of last update check', max_length=256, null=True, verbose_name='Update status'),
        ),
        migrations.AddField(
            model_name='config',
            name='app_update_install_status',
            field=models.CharField(help_text='Status of last update install', max_length=256, null=True, verbose_name='Install update status'),
        ),
    ]
