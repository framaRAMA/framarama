
from django.db import models


class ColorStroke(models.Model):
    color_stroke = models.CharField(
        max_length=16,
        verbose_name='Foreground color', help_text='The foreground color (lines, text) to use in HEX (RGB)')
    stroke_width = models.IntegerField(
        blank=True, null=True,
        verbose_name='Line width', help_text='The width to use when drawing lines')

    class Meta:
        abstract = True


class ColorFill(models.Model):
    color_fill = models.CharField(
        max_length=16, blank=True, null=True,
        verbose_name='Background color', help_text='The background color (fill) to use in HEX (RGB)')

    class Meta:
        abstract = True



class ColorAlpha(models.Model):
    color_alpha = models.IntegerField(
        blank=True, null=True,
        verbose_name='Transparency', help_text='The alpha value between 0 (transparent) and 100 (no transparency)')

    class Meta:
        abstract = True


class ColorStrokeFillAlpha(ColorStroke, ColorFill, ColorAlpha):

    class Meta:
        abstract = True


