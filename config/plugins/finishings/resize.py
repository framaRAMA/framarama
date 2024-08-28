import logging

from django import forms

from framarama.base import forms as base
from config.models import Finishing
from config.plugins import FinishingPluginImplementation
from config.forms.frame import FinishingForm
from config.utils import finishing


logger = logging.getLogger(__name__)


class ResizeForm(FinishingForm):
    resize_x = forms.CharField(
        max_length=64, widget=base.charFieldWidget(),
        label='X resizing', help_text='Resize to given image width')
    resize_y = forms.CharField(
        max_length=64, widget=base.charFieldWidget(),
        label='Y resizing', help_text='Resize to given image height')
    keep_aspect = forms.BooleanField(
        widget=base.booleanFieldWidget(), required=False,
        label='Keep aspect ratio', help_text='Resize only to given size as maximum while keeping aspect ratio')

    dependencies = {}

    class Meta(FinishingForm.Meta):
        entangled_fields = {'plugin_config': ['resize_x', 'resize_y', 'keep_aspect']}

    field_order = FinishingForm.Meta.untangled_fields + Meta.entangled_fields['plugin_config']


class Implementation(FinishingPluginImplementation):
    CAT = Finishing.CAT_RESIZE
    TITLE = 'Resize'
    DESCR = 'Apply horizontal and/or vertical resize'
    
    Form = ResizeForm
    
    def run(self, model, config, image, ctx):
        _adapter = ctx.get_adapter()
        _resize_x = config.resize_x.as_int()
        _resize_y = config.resize_y.as_int()
        _keep_aspect = config.keep_aspect.as_bool()
        _adapter.image_resize(image, _resize_x, _resize_y, _keep_aspect)
        return image


