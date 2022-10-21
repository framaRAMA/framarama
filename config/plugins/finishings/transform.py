import logging

from django.db import models

from framarama.base import forms as base
from config.models import Finishing
from config.plugins import PluginImplementation
from config.forms.frame import CreateFinishingForm, UpdateFinishingForm
from config.utils import finishing


logger = logging.getLogger(__name__)

TRANSFORM_CHOICES = [
    ('blur', 'Blur or sharpen image'),
    ('scale', 'Scale image'),
    ('rotate', 'Rotate image'),
]

FIELDS = [
    'mode',
    'factor',
]
WIDGETS = {
    'mode': base.selectFieldWidget(choices=TRANSFORM_CHOICES),
    'factor': base.charFieldWidget(),
}

class TransformModel(Finishing):
    finishing_ptr = models.OneToOneField(Finishing, on_delete=models.DO_NOTHING, parent_link=True, primary_key=True)
    mode = models.CharField(
        max_length=32,
        verbose_name='Type', help_text='The transformation to apply')
    factor = models.CharField(
        max_length=64,
        verbose_name='Factor', help_text='Factor to apply (>1/<1 for blur/sharpen, percent for scale, degrees for rotate)')

    class Meta:
        managed = False


class TransformCreateForm(CreateFinishingForm):
    dependencies = {}
    class Meta:
        model = TransformModel
        fields = CreateFinishingForm.fields(FIELDS)
        widgets = CreateFinishingForm.widgets(WIDGETS)


class TransformUpdateForm(UpdateFinishingForm):
    dependencies = {}
    class Meta:
        model = TransformModel
        fields = UpdateFinishingForm.fields(FIELDS)
        widgets = UpdateFinishingForm.widgets(WIDGETS)


class Implementation(PluginImplementation):
    CAT = Finishing.CAT_TRANSFORM
    TITLE = 'Transform'
    DESCR = 'Apply transformation on image (blur/scale/rotate)'
    
    Model = TransformModel
    CreateForm = TransformCreateForm
    UpdateForm = TransformUpdateForm
    
    def run(self, model, image, ctx):
        _adapter = ctx.get_adapter()
        _mode = model.mode.as_str()
        _factor = model.factor.as_float()
        if _mode == 'blur':
            _adapter.image_blur(image, _factor)
        elif _mode == 'scale':
            _adapter.image_scale(image, _factor/100)
        elif _mode == 'rotate':
            _adapter.image_rotate(image, _factor)
        return image


