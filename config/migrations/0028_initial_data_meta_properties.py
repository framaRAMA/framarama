
from django.db import migrations, models

from config.utils import finishing


def forward(apps, schema_editor):
    _adapter = finishing.WandImageProcessingAdapter()
    model = apps.get_model('config', 'Data')
    for row in model.objects.all():
        if row.meta and 'width' in row.meta:
            continue
        _image = _adapter.image_open(row.data_file.path)
        _meta = _adapter.image_meta(_image)
        row.meta.update({
            'width': _meta['width'],
            'height': _meta['height']
        })
        row.save(update_fields=['meta'])


def backward(apps, schema_editor):
    model = apps.get_model('config', 'Data')
    for row in model.objects.all():
        row.meta.pop('width')
        row.meta.pop('height')
        row.save(update_fields=['meta'])


class Migration(migrations.Migration):

    dependencies = [
        ('config', '0027_baseimagedata_data_meta'),
    ]

    operations = [
        migrations.RunPython(forward, reverse_code=backward),
    ]
