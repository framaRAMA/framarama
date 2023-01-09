import logging

from django.db import models

from framarama.base import forms as base
from config.models import Finishing
from config.plugins import PluginImplementation
from config.forms.frame import CreateFinishingForm, UpdateFinishingForm
from config.utils import finishing


logger = logging.getLogger(__name__)

FIELDS = [
    'url',
]
WIDGETS = {
    'url': base.charFieldWidget(),
}

class ImageModel(Finishing):
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
        _image = _adapter.image_open(_url)
        image.add_images(_image.get_images())
        return image


