
from django.db import migrations, models


def forward(apps, schema_editor):
    model = apps.get_model('config', 'Finishing')
    for row in model.objects.all():
        _plugin_config = row.plugin_config
        if row.plugin == 'shape' or row.plugin == 'text':
            _plugin_config['color_stroke'] = row.color_stroke
            _plugin_config['color_fill'] = row.color_fill
            _plugin_config['color_alpha'] = row.color_alpha
            _plugin_config['stroke_width'] = row.stroke_width
        elif row.plugin == 'image':
            _plugin_config['color_fill'] = row.color_fill
            _plugin_config['color_alpha'] = row.color_alpha
        else:
            continue
        row.plugin_config = _plugin_config
        row.save(update_fields=['plugin_config'])


def backward(apps, schema_editor):
    model = apps.get_model('config', 'Finishing')
    for row in model.objects.all():
        _plugin_config = row.plugin_config
        if row.plugin == 'shape' or row.plugin == 'text':
            row.color_stroke = _plugin_config['color_stroke']
            del _plugin_config['color_stroke']
            row.color_fill = _plugin_config['color_fill']
            del _plugin_config['color_fill']
            row.color_alpha = _plugin_config['color_alpha']
            del _plugin_config['color_alpha']
            row.stroke_width = _plugin_config['stroke_width']
            del _plugin_config['stroke_width']
        elif row.plugin == 'image':
            row.color_fill = _plugin_config['color_fill']
            del _plugin_config['color_fill']
            row.color_alpha = _plugin_config['color_alpha']
            del _plugin_config['color_alpha']
        else:
            continue
        row.plugin_config = _plugin_config
        row.save(update_fields=['plugin_config', 'color_stroke', 'color_fill', 'color_alpha', 'stroke_width'])


class Migration(migrations.Migration):

    dependencies = [
        ('config', '0018_displaystatus_items_error'),
    ]

    operations = [
        migrations.RunPython(forward, reverse_code=backward),
    ]
