import logging

from django.db import models

from framarama.base import forms as base
from config.models import Finishing
from config.plugins import PluginImplementation
from config.forms.frame import CreateFinishingForm, UpdateFinishingForm
from config.utils import finishing


logger = logging.getLogger(__name__)

TEXT_ALIGNMENTS = [
    ('left', 'Left'),
    ('right', 'Right'),
    ('center', 'Center'),
]


FIELDS = [
    'font',
    'text',
    'size',
    'alignment',
    'start_x',
    'start_y',
    'border',
    'border_radius',
    'border_alpha',
    'border_padding',
]
WIDGETS = {
    'text': base.charFieldWidget(),
    'font': base.charFieldWidget(),
    'size': base.charFieldWidget(),
    'alignment': base.selectFieldWidget(choices=TEXT_ALIGNMENTS),
    'start_x': base.charFieldWidget(),
    'start_y': base.charFieldWidget(),
    'border' : base.charFieldWidget(),
    'border_radius': base.charFieldWidget(),
    'border_alpha': base.charFieldWidget(),
    'border_padding': base.charFieldWidget(),
}

class TextModel(Finishing):
    finishing_ptr = models.OneToOneField(Finishing, on_delete=models.DO_NOTHING, parent_link=True, primary_key=True)
    text = models.CharField(
        max_length=256,
        verbose_name='Text', help_text='Text to show')
    font = models.CharField(
        max_length=64,
        verbose_name='Font', help_text='Font name to use (e.g. Arial, Helvetica, Courier)')
    size = models.CharField(
        max_length=64,
        verbose_name='Size', help_text='Font size')
    start_x = models.CharField(
        max_length=64,
        verbose_name='X position', help_text='Starting point horizontally')
    start_y = models.CharField(
        max_length=64,
        verbose_name='Y position', help_text='Starting point vertically')
    alignment = models.CharField(
        max_length=16, choices = TEXT_ALIGNMENTS,
        verbose_name='Alignment', help_text='How to align the text')
    border = models.CharField(
        max_length=16, blank=True, null=True,
        verbose_name='Border', help_text='Draw border around the text with given width')
    border_radius = models.CharField(
        max_length=16, blank=True, null=True,
        verbose_name='Border radius', help_text='Use rounded corners when drawing border')
    border_alpha = models.IntegerField(
        blank=True, null=True,
        verbose_name='Border transparency', help_text='The border alpha value (transparency) between 0 and 100')
    border_padding = models.IntegerField(
        blank=True, null=True,
        verbose_name='Border padding', help_text='Spacing between text and border')

    class Meta:
        managed = False


class TextCreateForm(CreateFinishingForm):
    class Meta:
        model = TextModel
        fields = CreateFinishingForm.fields(FIELDS)
        widgets = CreateFinishingForm.widgets(WIDGETS)


class TextUpdateForm(UpdateFinishingForm):
    class Meta:
        model = TextModel
        fields = UpdateFinishingForm.fields(FIELDS)
        widgets = UpdateFinishingForm.widgets(WIDGETS)


class Implementation(PluginImplementation):
    CAT = Finishing.CAT_TEXT
    TITLE = 'Text'
    DESCR = 'Write some text to given position'
    
    Model = TextModel
    CreateForm = TextCreateForm
    UpdateForm = TextUpdateForm
    
    def run(self, model, image, ctx):
        _adapter = ctx.get_adapter()
        _start_x = model.start_x.as_int()
        _start_y = model.start_y.as_int()
        _color_stroke = model.color_stroke.as_str()
        _color_fill = model.color_fill.as_str()
        _color_alpha = model.color_alpha.as_int()
        _font = model.font.as_str()
        _text = model.text.as_str()
        _size = model.size.as_int()
        _alignment = model.alignment.as_str()
        _border = model.border.as_int()
        _border_radius = model.border_radius.as_int()
        _border_alpha = model.border_alpha.as_int()
        _border_padding = model.border_padding.as_int()
        
        _pos = finishing.Position(_start_x, _start_y)
        _brush = finishing.Brush(
            stroke_color=finishing.Color(_color_stroke, _color_alpha))
        if _color_fill:
            _fill_color = finishing.Color(_color_fill, _border_alpha)
        else:
            _fill_color = None
        _brush_border = finishing.Brush(
            stroke_color=finishing.Color(_color_stroke, _border_alpha),
            stroke_width=_border,
            fill_color=_fill_color)
        _text = finishing.Text(_text, font=_font, size=_size, alignment=_alignment)
        _adapter.draw_text(image, _pos, _text, _brush, border_brush=_brush_border, border_radius=_border_radius, border_padding=_border_padding)
        return image

