# Generated by Django 4.0.4 on 2023-01-24 16:30

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('config', '0019_finishing_fields_to_plugin_data'),
    ]

    operations = [
        migrations.AlterField(
            model_name='displayitem',
            name='display',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='config.display'),
        ),
    ]