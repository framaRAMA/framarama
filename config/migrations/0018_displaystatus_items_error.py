# Generated by Django 4.0.4 on 2023-01-06 07:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('config', '0017_alter_displaystatus_disk_data_free_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='displaystatus',
            name='items_error',
            field=models.IntegerField(blank=True, help_text='Total amount of items with errors', null=True, verbose_name='Items error'),
        ),
    ]
