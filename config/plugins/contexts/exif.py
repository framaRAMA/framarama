import logging

from django import forms
from django.template import Context

from framarama.base import forms as base
from config.models import FrameContext
from config.plugins import ContextPluginImplementation
from config.forms.frame import ContextForm
from config.utils import context


logger = logging.getLogger(__name__)


class ExifForm(ContextForm):
    image = forms.CharField(
        max_length=256, required=False, widget=base.charFieldWidget(),
        label='Images', help_text='Specify images to extract exif information (defaults to "default")')

    class Meta(ContextForm.Meta):
        entangled_fields = {'plugin_config': ['image']}

    field_order = ContextForm.Meta.untangled_fields + Meta.entangled_fields['plugin_config']


class Implementation(ContextPluginImplementation):
    CAT = FrameContext.CAT_EXIF
    TITLE = 'Exif'
    DESCR = 'Extract and provide EXIF information'
    
    Form = ExifForm

    def run(self, model, config, image, ctx):
        _image = config.image.as_str()

        _adapter = ctx.get_adapter()

        _resolvers = {'exifs': {}}
        for _name, _img in self.get_images(ctx, _image).items():
            _image_exif = _adapter.image_exif(_img) if _img.get_images() else {}
            _resolver = context.MapResolver(_image_exif)
            if _name == 'default':
                _resolvers['exif'] = _resolver
            else:
                _resolvers['exifs'][_name] = _resolver

        return _resolvers

