import logging

from django import forms

from framarama.base import forms as base
from config.models import Finishing
from config.plugins import FinishingPluginImplementation
from config.forms.frame import FinishingForm
from config.utils import finishing


logger = logging.getLogger(__name__)

TRANSFORM_CHOICES = [
    ('blur', 'Blur or sharpen image'),
    ('scale', 'Scale image'),
    ('rotate', 'Rotate image'),
]


class TransformForm(FinishingForm):
    mode = forms.CharField(
        max_length=32, widget=base.selectFieldWidget(choices=TRANSFORM_CHOICES),
        label='Type', help_text='The transformation to apply')
    factor = forms.CharField(
        max_length=64, widget=base.charFieldWidget(),
        label='Factor', help_text='Factor to apply (>1/<1 for blur/sharpen, percent for scale, degrees for rotate)')

    dependencies = {}

    class Meta(FinishingForm.Meta):
        entangled_fields = {'plugin_config': ['mode', 'factor']}

    field_order = FinishingForm.Meta.untangled_fields + Meta.entangled_fields['plugin_config']


class Implementation(FinishingPluginImplementation):
    CAT = Finishing.CAT_TRANSFORM
    TITLE = 'Transform'
    DESCR = 'Apply transformation on image (blur/scale/rotate)'
    
    Form = TransformForm
    
    def run(self, model, config, image, ctx):
        _adapter = ctx.get_adapter()
        _mode = config.mode.as_str()
        _factor = config.factor.as_float()
        if _mode == 'blur':
            _adapter.image_blur(image, _factor)
        elif _mode == 'scale':
            _adapter.image_scale(image, _factor/100)
        elif _mode == 'rotate':
            _adapter.image_rotate(image, _factor)
        return image


