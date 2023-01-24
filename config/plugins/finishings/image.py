import logging

from django.db import models

from framarama.base import forms as base
from config.models import Finishing
from config.plugins import PluginImplementation
from config.plugins.finishings import ColorFill, ColorAlpha
from config.forms.frame import CreateFinishingForm, UpdateFinishingForm
from config.utils import finishing


logger = logging.getLogger(__name__)

FIELDS = [
    'url',
]
WIDGETS = {
    'url': base.charFieldWidget(),
}

class ImageModel(Finishing, ColorFill, ColorAlpha):
    finishing_ptr = models.OneToOneField(Finishing, on_delete=models.DO_NOTHING, parent_link=True, primary_key=True)
    url = models.CharField(
        max_length=256,
        verbose_name='URL', help_text='The URL to the resource to load the image from')

    class Meta:
        managed = False


class ImageCreateForm(CreateFinishingForm):
    dependencies = {}
    class Meta:
        model = ImageModel
        fields = CreateFinishingForm.fields(FIELDS)
        widgets = CreateFinishingForm.widgets(WIDGETS)


class ImageUpdateForm(UpdateFinishingForm):
    dependencies = {}
    class Meta:
        model = ImageModel
        fields = UpdateFinishingForm.fields(FIELDS)
        widgets = UpdateFinishingForm.widgets(WIDGETS)


class Implementation(PluginImplementation):
    CAT = Finishing.CAT_IMAGE
    TITLE = 'Image'
    DESCR = 'Load image from a given resource URL'
    
    Model = ImageModel
    CreateForm = ImageCreateForm
    UpdateForm = ImageUpdateForm
    
    def run(self, model, image, ctx):
        _adapter = ctx.get_adapter()
        _url = model.url.as_str()
        _color_fill = finishing.Color(model.color_fill.as_str()) if model.color_fill.as_str() else None
        _color_alpha = model.color_alpha.as_int()
        _image = _adapter.image_open(_url, _color_fill)
        if _color_alpha:
            _adapter.image_alpha(_image, _color_fill, _color_alpha)
        return _image


