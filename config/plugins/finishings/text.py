import logging

from django import forms

from framarama.base import forms as base
from config.models import Finishing
from config.plugins import FinishingPluginImplementation
from config.plugins.finishings import ColorStrokeFillAlpha
from config.forms.frame import FinishingForm
from config.utils import finishing


logger = logging.getLogger(__name__)

TEXT_ALIGNMENTS = [
    ('left', 'Left'),
    ('right', 'Right'),
    ('center', 'Center'),
]
#TEXT_VERTICAL_ALIGNMENTS = [
#    ('default', 'Default'),
#    ('center', 'Center'),
#]


class TextForm(FinishingForm, ColorStrokeFillAlpha):
    font = forms.CharField(
        max_length=64, widget=base.charFieldWidget(),
        label='Font', help_text='Font name to use (e.g. Arial, Helvetica, Courier)')
    weight = forms.CharField(
        max_length=64, required=False, widget=base.charFieldWidget(),
        label='Font weight', help_text='Front weight (e.g. 400 for normal, 700 for bold, 900 for bolder)')
    text = forms.CharField(
        max_length=1024, widget=base.textareaFieldWidget(),
        label='Text', help_text='Text to show')
    size = forms.CharField(
        max_length=64, widget=base.charFieldWidget(),
        label='Size', help_text='Font size')
    start_x = forms.CharField(
        max_length=64, widget=base.charFieldWidget(),
        label='X position', help_text='Starting point horizontally')
    start_y = forms.CharField(
        max_length=64, widget=base.charFieldWidget(),
        label='Y position', help_text='Starting point vertically')
    alignment = forms.CharField(
        max_length=16, widget=base.selectFieldWidget(choices=TEXT_ALIGNMENTS),
        label='Alignment', help_text='How to align the text')
    #alignment_vertical = forms.CharField(
    #    max_length=16, widget=base.selectFieldWidget(choices=TEXT_VERTICAL_ALIGNMENTS),
    #    label='Vertical alignment', help_text='How to align the text vertically')
    border = forms.CharField(
        max_length=16, required=False, widget=base.charFieldWidget(),
        label='Border', help_text='Draw border around the text with given width')
    border_radius = forms.CharField(
        max_length=16, required=False, widget=base.charFieldWidget(),
        label='Border radius', help_text='Use rounded corners when drawing border')
    border_alpha = forms.IntegerField(
        required=False, widget=base.charFieldWidget(),
        label='Border transparency', help_text='The border alpha value between 0 (transparent) and 100 (no transparency)')
    border_padding = forms.IntegerField(
        required=False, widget=base.charFieldWidget(),
        label='Border padding', help_text='Spacing between text and border')
    rotate = forms.IntegerField(
        required=False, widget=base.charFieldWidget(),
        label='Rotation', help_text='Rotate text with given angle')

    dependencies = {}

    class Meta(FinishingForm.Meta):
        entangled_fields = {'plugin_config':
            ['font', 'weight', 'text', 'size'] +
            ColorStrokeFillAlpha.Meta.entangled_fields['plugin_config'] +
            ['alignment', 'start_x', 'start_y', 'border', 'border_radius', 'border_alpha', 'border_padding', 'rotate']
        }

    field_order = FinishingForm.Meta.untangled_fields + Meta.entangled_fields['plugin_config']


class Implementation(FinishingPluginImplementation):
    CAT = Finishing.CAT_TEXT
    TITLE = 'Text'
    DESCR = 'Write some text to given position'
    
    Form = TextForm
    
    def run(self, model, config, image, ctx):
        _adapter = ctx.get_adapter()
        _start_x = config.start_x.as_int()
        _start_y = config.start_y.as_int()
        _color_stroke = config.color_stroke.as_str()
        _color_fill = config.color_fill.as_str()
        _color_alpha = config.color_alpha.as_int()
        _stroke_width = config.stroke_width.as_int()
        _font = config.font.as_str()
        _text = config.text.as_str()
        _size = config.size.as_int()
        _weight = config.weight.as_int()
        _alignment = config.alignment.as_str()
        _alignment_vertical = config.alignment_vertical.as_str()
        _border = config.border.as_int()
        _border_radius = config.border_radius.as_int()
        _border_alpha = config.border_alpha.as_int()
        _border_padding = config.border_padding.as_int()
        _rotate = config.rotate.as_int()
        
        _pos = finishing.Position(_start_x, _start_y)
        _brush = finishing.Brush(
            stroke_color=finishing.Color(_color_stroke, _color_alpha),
            stroke_width=_stroke_width)
        if _color_fill:
            _fill_color = finishing.Color(_color_fill, _border_alpha)
        else:
            _fill_color = None
        _brush_border = finishing.Brush(
            stroke_color=finishing.Color(_color_stroke, _border_alpha),
            stroke_width=_border,
            fill_color=_fill_color)
        _text = finishing.Text(_text, font=_font, size=_size, weight=_weight, alignment=_alignment, alignment_vertical=_alignment_vertical)
        _adapter.draw_text(image, _pos, _text, _brush, border_brush=_brush_border, border_radius=_border_radius, border_padding=_border_padding, rotate=_rotate)
        return image

