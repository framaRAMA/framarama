# Generated by Django 4.2.20 on 2025-04-19 19:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('config', '0035_settings'),
    ]

    operations = [
        migrations.AddField(
            model_name='source',
            name='enabled',
            field=models.BooleanField(default=True, verbose_name='Enabled'),
        ),
    ]
