import logging

from django.db import models

from framarama.base import forms as base
from config.models import Finishing
from config.plugins import PluginImplementation
from config.forms.frame import CreateFinishingForm, UpdateFinishingForm
from config.utils import finishing


logger = logging.getLogger(__name__)

ALIGNMENT_CHOICES = [
    ('center', 'Align all images in the middle'),
    ('top', 'Align all images at top'),
    ('bottom', 'Align all images at bottom'),
    ('left', 'Align all images at left'),
    ('right', 'Align all images at right'),
]

FIELDS = [
    'alignment',
]
WIDGETS = {
    'alignment': base.selectFieldWidget(choices=ALIGNMENT_CHOICES),
}

class MergeModel(Finishing):
    finishing_ptr = models.OneToOneField(Finishing, on_delete=models.DO_NOTHING, parent_link=True, primary_key=True)
    alignment = models.CharField(
        max_length=32,
        verbose_name='Alignment', help_text='Align images as selected when merging')

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


class Implementation(PluginImplementation):
    CAT = Finishing.CAT_MERGE
    TITLE = 'Merge'
    DESCR = 'Merge multiple images into one'
    
    Model = MergeModel
    CreateForm = MergeCreateForm
    UpdateForm = MergeUpdateForm
    
    def run(self, model, image, ctx):
        _adapter = ctx.get_adapter()
        _alignment = model.alignment.as_str()
        _adapter.image_merge(image, _alignment)
        return image


