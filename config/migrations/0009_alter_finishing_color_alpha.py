# Generated by Django 4.0.4 on 2022-11-13 18:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('config', '0008_mergemodel_resizemodel_transformmodel'),
    ]

    operations = [
        migrations.AlterField(
            model_name='finishing',
            name='color_alpha',
            field=models.IntegerField(blank=True, help_text='The alpha value between 0 (transparent) and 100 (no transparency)', null=True, verbose_name='Transparency'),
        ),
    ]