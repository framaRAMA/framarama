import logging

from django import forms

from framarama.base import forms as base
from config.models import Finishing
from config.plugins import FinishingPluginImplementation
from config.plugins.finishings import ColorStrokeFillAlpha
from config.forms.frame import FinishingForm
from config.utils import finishing


logger = logging.getLogger(__name__)

SHAPE_CHOICES = [
    ('line', 'Line'),
    ('circle', 'Circle'),
    ('rectangle', 'Rectangle'),
]

FIELD_DEPENDENCIES = {
  'shape' : {
    'circle': ['start_x', 'start_y'],
    'line': ['start_x']
  }
}


class ShapeForm(FinishingForm, ColorStrokeFillAlpha):
    shape = forms.CharField(
        max_length=32, widget=base.selectFieldWidget(choices=SHAPE_CHOICES),
        label='Shape', help_text='The shapw to draw')
    start_x = forms.CharField(
        max_length=64, widget=base.charFieldWidget(),
        label='X position', help_text='Starting point horizontally')
    start_y = forms.CharField(
        max_length=64, widget=base.charFieldWidget(),
        label='Y position', help_text='Starting point vertically')
    size_x = forms.CharField(
        max_length=64, widget=base.charFieldWidget(),
        label='X dimension', help_text='Ending point horizontally (or width)')
    size_y = forms.CharField(
        max_length=64, widget=base.charFieldWidget(),
        label='Y dimension', help_text='Ending point vertically (or height)')

    dependencies = FIELD_DEPENDENCIES

    class Meta(FinishingForm.Meta):
        entangled_fields = {'plugin_config':
            ['shape', 'start_x', 'start_y', 'size_x', 'size_y'] +
            ColorStrokeFillAlpha.Meta.entangled_fields['plugin_config']
        }

    field_order = FinishingForm.Meta.untangled_fields + Meta.entangled_fields['plugin_config']


class Implementation(FinishingPluginImplementation):
    CAT = Finishing.CAT_SHAPE
    TITLE = 'Shape'
    DESCR = 'Draw a given shape'
    
    Form = ShapeForm
    
    def run(self, model, config, image, ctx):
        _adapter = ctx.get_adapter()
        _shape = config.shape.as_str()
        _color_alpha = config.color_alpha.as_int()
        _color_stroke = finishing.Color(config.color_stroke.as_str(), _color_alpha)
        _color_fill = finishing.Color(config.color_fill.as_str(), _color_alpha)
        _stroke_width = config.stroke_width.as_int()
        _start = finishing.Position(config.start_x.as_int(), config.start_y.as_int())
        _size = finishing.Size(config.size_x.as_int(), config.size_y.as_int())
        _brush = finishing.Brush(stroke_color=_color_stroke, stroke_width=_stroke_width, fill_color=_color_fill)
        if _shape == 'line':
            _adapter.draw_line(image, _start, _start + _size, _brush)
        elif _shape == 'rectangle':
            _adapter.draw_rect(image, _start, _start + _size, _brush)
        elif _shape == 'circle':
            _adapter.draw_circle(image, _start, _size, _brush)
        return image


