import logging

from django import forms

from framarama.base import forms as base
from config.models import Finishing
from config.plugins import FinishingPluginImplementation
from config.plugins.finishings import ColorFill, ColorAlpha
from config.forms.frame import FinishingForm
from config.utils import finishing


logger = logging.getLogger(__name__)


class ImageForm(FinishingForm, ColorFill, ColorAlpha):
    url = forms.CharField(
        max_length=256, widget=base.charFieldWidget(),
        label='URL', help_text='The URL to the resource to load the image from')

    dependencies = {}

    class Meta(FinishingForm.Meta):
        entangled_fields = {'plugin_config':
            ColorFill.Meta.entangled_fields['plugin_config'] +
            ColorAlpha.Meta.entangled_fields['plugin_config'] +
            ['url']
        }

    field_order = FinishingForm.Meta.untangled_fields + Meta.entangled_fields['plugin_config']


class Implementation(FinishingPluginImplementation):
    CAT = Finishing.CAT_IMAGE
    TITLE = 'Image'
    DESCR = 'Load image from a given resource URL'
    
    Form = ImageForm
    
    def run(self, model, config, image, ctx):
        _adapter = ctx.get_adapter()
        _url = config.url.as_str()
        _color_fill = finishing.Color(config.color_fill.as_str()) if config.color_fill.as_str() else None
        _color_alpha = config.color_alpha.as_int()
        _image = _adapter.image_open(_url, _color_fill)
        if _color_alpha:
            _adapter.image_alpha(_image, _color_fill, _color_alpha)
        return _image


