import logging

from django.db import models
from django.template import Context, Template

from framarama.base import forms as base
from config.models import FrameContext
from config.plugins import PluginImplementation
from config.forms.frame import CreateContextForm, UpdateContextForm
from config.utils import context


logger = logging.getLogger(__name__)

FIELDS = [
    'image',
]
WIDGETS = {
    'image': base.charFieldWidget(),
}


class ExifModel(FrameContext):
    frame_ptr = models.OneToOneField(FrameContext, on_delete=models.DO_NOTHING, parent_link=True, primary_key=True)
    image = models.CharField(
        max_length=256, blank=True,
        verbose_name='Images', help_text='Specify images to extract exif information (defaults to "default")')

    class Meta:
        managed = False


class ExifCreateForm(CreateContextForm):
    class Meta:
        model = ExifModel
        fields = CreateContextForm.fields(FIELDS)
        widgets = CreateContextForm.widgets(WIDGETS)


class ExifUpdateForm(UpdateContextForm):
    class Meta:
        model = ExifModel
        fields = UpdateContextForm.fields(FIELDS)
        widgets = UpdateContextForm.widgets(WIDGETS)


class Implementation(PluginImplementation):
    CAT = FrameContext.CAT_EXIF
    TITLE = 'Exif'
    DESCR = 'Extract and provide EXIF information'
    
    Model = ExifModel
    CreateForm = ExifCreateForm
    UpdateForm = ExifUpdateForm

    def run(self, model, image, ctx):
        _adapter = ctx.get_adapter()
        _image_exif = _adapter.image_exif(image) if image.get_images() else {}
        return {'exif': context.MapResolver(_image_exif)}

