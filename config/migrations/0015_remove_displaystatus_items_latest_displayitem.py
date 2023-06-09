# Generated by Django 4.0.4 on 2022-12-28 10:59

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('config', '0014_alter_displaystatus_items_updated_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='displaystatus',
            name='items_latest',
        ),
        migrations.CreateModel(
            name='DisplayItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('updated', models.DateTimeField(auto_now=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('date_first_seen', models.DateTimeField(blank=True, help_text='Date when the item was first shown on display', null=True, verbose_name='First seen')),
                ('date_last_seen', models.DateTimeField(blank=True, help_text='Date when the item was last shown on the display', null=True, verbose_name='Last seen')),
                ('count_hit', models.IntegerField(blank=True, help_text='Amount of hits for this item', null=True, verbose_name='Hits')),
                ('display', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='item', to='config.display')),
                ('item', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='display', to='config.item')),
            ],
            options={
                'db_table': 'config_display_item',
                'ordering': ['-created'],
            },
        ),
    ]
