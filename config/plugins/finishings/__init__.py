
from django import forms

from framarama.base import forms as base


class ColorStroke(forms.Form):
    color_stroke = forms.CharField(
        max_length=16, widget=base.charFieldWidget(),
        label='Foreground color', help_text='The foreground color (lines, text) to use in HEX (RGB)')
    stroke_width = forms.IntegerField(
        required=False, widget=base.charFieldWidget(),
        label='Line width', help_text='The width to use when drawing lines')

    class Meta:
        entangled_fields = {'plugin_config': ['color_stroke', 'stroke_width']}


class ColorFill(forms.Form):
    color_fill = forms.CharField(
        max_length=16, required=False, widget=base.charFieldWidget(),
        label='Background color', help_text='The background color (fill) to use in HEX (RGB)')

    class Meta:
        entangled_fields = {'plugin_config': ['color_fill']}


class ColorAlpha(forms.Form):
    color_alpha = forms.IntegerField(
        required=False, widget=base.charFieldWidget(),
        label='Transparency', help_text='The alpha value between 0 (transparent) and 100 (no transparency)')

    class Meta:
        entangled_fields = {'plugin_config': ['color_alpha']}


class ColorStrokeFillAlpha(ColorStroke, ColorFill, ColorAlpha):

    class Meta:
        entangled_fields = {'plugin_config':
            ColorStroke.Meta.entangled_fields['plugin_config'] +
            ColorFill.Meta.entangled_fields['plugin_config'] +
            ColorAlpha.Meta.entangled_fields['plugin_config']
        }


