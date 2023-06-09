# Generated by Django 4.0.4 on 2022-11-17 21:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('config', '0009_alter_finishing_color_alpha'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='datamodel',
            name='sourcestep_ptr',
        ),
        migrations.RemoveField(
            model_name='httpmodel',
            name='sourcestep_ptr',
        ),
        migrations.RemoveField(
            model_name='mergemodel',
            name='finishing_ptr',
        ),
        migrations.RemoveField(
            model_name='resizemodel',
            name='finishing_ptr',
        ),
        migrations.RemoveField(
            model_name='shapemodel',
            name='finishing_ptr',
        ),
        migrations.RemoveField(
            model_name='textmodel',
            name='finishing_ptr',
        ),
        migrations.RemoveField(
            model_name='transformmodel',
            name='finishing_ptr',
        ),
        migrations.AlterField(
            model_name='finishing',
            name='color_stroke',
            field=models.CharField(help_text='The foreground color (lines, text) to use in HEX (RGB)', max_length=16, verbose_name='Foreground color'),
        ),
        migrations.DeleteModel(
            name='CustomModel',
        ),
        migrations.DeleteModel(
            name='DataModel',
        ),
        migrations.DeleteModel(
            name='HttpModel',
        ),
        migrations.DeleteModel(
            name='MergeModel',
        ),
        migrations.DeleteModel(
            name='ResizeModel',
        ),
        migrations.DeleteModel(
            name='ShapeModel',
        ),
        migrations.DeleteModel(
            name='TextModel',
        ),
        migrations.DeleteModel(
            name='TransformModel',
        ),
    ]
