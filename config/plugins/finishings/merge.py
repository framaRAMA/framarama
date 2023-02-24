import logging

from django.db import models

from framarama.base import forms as base
from config.models import Finishing
from config.plugins import FinishingPluginImplementation
from config.forms.frame import CreateFinishingForm, UpdateFinishingForm
from config.utils import finishing


logger = logging.getLogger(__name__)

ALIGNMENT_CHOICES = [
    ('coords', 'Align all images at given coordiates'),
    ('center', 'Align all images in the middle'),
    ('top', 'Align all images at top'),
    ('bottom', 'Align all images at bottom'),
    ('left', 'Align all images at left'),
    ('right', 'Align all images at right'),
    ('top-left', 'Align all images at top left corner'),
    ('top-right', 'Align all images at top right corner'),
    ('bottom-left', 'Align all images at bottom left corner'),
    ('bottom-right', 'Align all images at bottom right corner'),
]

FIELDS = [
    'alignment',
    'left',
    'top',
]
WIDGETS = {
    'alignment': base.selectFieldWidget(choices=ALIGNMENT_CHOICES),
    'left': base.charFieldWidget(),
    'top': base.charFieldWidget(),
}

class MergeModel(Finishing):
    finishing_ptr = models.OneToOneField(Finishing, on_delete=models.DO_NOTHING, parent_link=True, primary_key=True)
    alignment = models.CharField(
        max_length=32,
        verbose_name='Alignment', help_text='Align images when merging (use predefined alignments or coordinates below)')
    left = models.CharField(
        max_length=64, blank=True, null=True,
        verbose_name='X position', help_text='The horizontal position for the alignment')
    top = models.CharField(
        max_length=64, blank=True, null=True,
        verbose_name='Y position', help_text='The vertical position for the alignment')

    class Meta:
        managed = False


class MergeCreateForm(CreateFinishingForm):
    dependencies = {}
    class Meta:
        model = MergeModel
        fields = CreateFinishingForm.fields(FIELDS)
        widgets = CreateFinishingForm.widgets(WIDGETS)


class MergeUpdateForm(UpdateFinishingForm):
    dependencies = {}
    class Meta:
        model = MergeModel
        fields = UpdateFinishingForm.fields(FIELDS)
        widgets = UpdateFinishingForm.widgets(WIDGETS)


class Implementation(FinishingPluginImplementation):
    CAT = Finishing.CAT_MERGE
    TITLE = 'Merge'
    DESCR = 'Merge multiple images into one'
    
    Model = MergeModel
    CreateForm = MergeCreateForm
    UpdateForm = MergeUpdateForm
    
    def run(self, model, image, ctx):
        _adapter = ctx.get_adapter()
        _alignment = model.alignment.as_str()
        _coordinates = [model.left.as_int(), model.top.as_int()] if _alignment == 'coords' else None
        _image = _adapter.image_merge(image, _alignment, _coordinates)
        return _image


