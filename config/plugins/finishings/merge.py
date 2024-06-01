import logging

from django import forms

from framarama.base import forms as base
from config.models import Finishing
from config.plugins import FinishingPluginImplementation
from config.forms.frame import FinishingForm
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


class MergeForm(FinishingForm):
    alignment = forms.CharField(
        max_length=32, widget=base.selectFieldWidget(choices=ALIGNMENT_CHOICES),
        label='Alignment', help_text='Align images when merging (use predefined alignments or coordinates below)')
    left = forms.CharField(
        max_length=64, required=False, widget=base.charFieldWidget(),
        label='X position', help_text='The horizontal position for the alignment')
    top = forms.CharField(
        max_length=64, required=False, widget=base.charFieldWidget(),
        label='Y position', help_text='The vertical position for the alignment')

    dependencies = {}

    class Meta(FinishingForm.Meta):
        entangled_fields = {'plugin_config': ['alignment', 'left', 'top']}

    field_order = FinishingForm.Meta.untangled_fields + Meta.entangled_fields['plugin_config']


class Implementation(FinishingPluginImplementation):
    CAT = Finishing.CAT_MERGE
    TITLE = 'Merge'
    DESCR = 'Merge multiple images into one'
    
    Form = MergeForm
    
    def run(self, model, config, image, ctx):
        _adapter = ctx.get_adapter()
        _alignment = config.alignment.as_str()
        _coordinates = [config.left.as_int(), config.top.as_int()] if _alignment == 'coords' else None
        _image = _adapter.image_merge(image, _alignment, _coordinates)
        return _image


