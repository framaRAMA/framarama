import logging

from django.db import models

from framarama.base import forms as base
from config.models import Finishing
from config.plugins import PluginImplementation
from config.forms.frame import CreateFinishingForm, UpdateFinishingForm
from config.utils import finishing


logger = logging.getLogger(__name__)

FIELDS = [
    'resize_x',
    'resize_y',
    'keep_aspect',
]
WIDGETS = {
    'resize_x': base.charFieldWidget(),
    'resize_y': base.charFieldWidget(),
    'keep_aspect': base.booleanFieldWidget(),
}

class ResizeModel(Finishing):
    finishing_ptr = models.OneToOneField(Finishing, on_delete=models.DO_NOTHING, parent_link=True, primary_key=True)
    resize_x = models.CharField(
        max_length=64,
        verbose_name='X resizing', help_text='Resize to given image width')
    resize_y = models.CharField(
        max_length=64,
        verbose_name='Y resizing', help_text='Resize to given image height')
    keep_aspect = models.BooleanField(
        verbose_name='Keep aspect ratio', help_text='Resize only to given size as maximum while keeping aspect ratio')

    class Meta:
        managed = False


class ResizeCreateForm(CreateFinishingForm):
    dependencies = {}
    class Meta:
        model = ResizeModel
        fields = CreateFinishingForm.fields(FIELDS)
        widgets = CreateFinishingForm.widgets(WIDGETS)


class ResizeUpdateForm(UpdateFinishingForm):
    dependencies = {}
    class Meta:
        model = ResizeModel
        fields = UpdateFinishingForm.fields(FIELDS)
        widgets = UpdateFinishingForm.widgets(WIDGETS)


class Implementation(PluginImplementation):
    CAT = Finishing.CAT_RESIZE
    TITLE = 'Resize'
    DESCR = 'Apply horizontal and/or vertical resize'
    
    Model = ResizeModel
    CreateForm = ResizeCreateForm
    UpdateForm = ResizeUpdateForm
    
    def run(self, model, image, ctx):
        _adapter = ctx.get_adapter()
        _resize_x = model.resize_x.as_int()
        _resize_y = model.resize_y.as_int()
        _keep_aspect = model.keep_aspect.as_bool()
        _adapter.image_resize(image, _resize_x, _resize_y, _keep_aspect)
        return image


