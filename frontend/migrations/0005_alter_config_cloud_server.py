# Generated by Django 4.0.4 on 2022-11-15 18:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('frontend', '0004_config_date_app_startup_config_date_items_update'),
    ]

    operations = [
        migrations.AlterField(
            model_name='config',
            name='cloud_server',
            field=models.CharField(help_text='Remote server URL', max_length=255, verbose_name='Server'),
        ),
    ]
