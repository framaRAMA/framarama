import logging

from django.db import models

from framarama.base import forms as base
from config.models import Finishing
from config.plugins import PluginImplementation
from config.forms.frame import CreateFinishingForm, UpdateFinishingForm
from config.utils import finishing


logger = logging.getLogger(__name__)

SHAPE_CHOICES = [
    ('line', 'Line'),
    ('circle', 'Circle'),
    ('rectangle', 'Rectangle'),
]


FIELDS = [
    'shape',
    'start_x',
    'start_y',
    'size_x',
    'size_y',
]
FIELD_DEPENDENCIES = {
  'shape' : {
    'circle': ['start_x', 'start_y'],
    'line': ['start_x']
  }
}
WIDGETS = {
    'shape': base.selectFieldWidget(choices=SHAPE_CHOICES),
    'start_x': base.charFieldWidget(),
    'start_y': base.charFieldWidget(),
    'size_x': base.charFieldWidget(),
    'size_y': base.charFieldWidget(),
}

class ShapeModel(Finishing):
    finishing_ptr = models.OneToOneField(Finishing, on_delete=models.DO_NOTHING, parent_link=True, primary_key=True)
    shape = models.CharField(
        max_length=32,
        verbose_name='Shape', help_text='The shapw to draw')
    start_x = models.CharField(
        max_length=64,
        verbose_name='X position', help_text='Starting point horizontally')
    start_y = models.CharField(
        max_length=64,
        verbose_name='Y position', help_text='Starting point vertically')
    size_x = models.CharField(
        max_length=64,
        verbose_name='X dimension', help_text='Ending point horizontally (or width)')
    size_y = models.CharField(
        max_length=64,
        verbose_name='Y dimension', help_text='Ending point vertically (or height)')

    class Meta:
        managed = False


class ShapeCreateForm(CreateFinishingForm):
    dependencies = FIELD_DEPENDENCIES
    class Meta:
        model = ShapeModel
        fields = CreateFinishingForm.fields(FIELDS)
        widgets = CreateFinishingForm.widgets(WIDGETS)


class ShapeUpdateForm(UpdateFinishingForm):
    dependencies = FIELD_DEPENDENCIES
    class Meta:
        model = ShapeModel
        fields = UpdateFinishingForm.fields(FIELDS)
        widgets = UpdateFinishingForm.widgets(WIDGETS)


class Implementation(PluginImplementation):
    CAT = Finishing.CAT_SHAPE
    TITLE = 'Shape'
    DESCR = 'Draw a given shape'
    
    Model = ShapeModel
    CreateForm = ShapeCreateForm
    UpdateForm = ShapeUpdateForm
    
    def run(self, model, image, ctx):
        _adapter = ctx.get_adapter()
        _shape = model.shape.as_str()
        _color_alpha = model.color_alpha.as_int()
        _color_stroke = finishing.Color(model.color_stroke.as_str(), _color_alpha)
        _color_fill = finishing.Color(model.color_fill.as_str(), _color_alpha)
        _stroke_width = model.stroke_width.as_int()
        _start = finishing.Position(model.start_x.as_int(), model.start_y.as_int())
        _size = finishing.Size(model.size_x.as_int(), model.size_y.as_int())
        _brush = finishing.Brush(stroke_color=_color_stroke, stroke_width=_stroke_width, fill_color=_color_fill)
        if _shape == 'line':
            _adapter.draw_line(image, _start, _start + _size, _brush)
        elif _shape == 'rectangle':
            _adapter.draw_rect(image, _start, _start + _size, _brush)
        elif _shape == 'circle':
            _adapter.draw_circle(image, _start, _size, _brush)
        return image


