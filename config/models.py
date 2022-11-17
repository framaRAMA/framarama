import re

from django.db import models
from django.contrib.auth.models import User

from framarama.base.models import BaseModel, PluginModel


MIME_CHOICES = [
  ('', 'Auto (automatically detect mime type)'),
  ('text/csv', 'CSV (comma separated data)'),
  ('application/json', 'JSON'),
  ('text/plain', 'Plain text'),
]

DEVICE_CHOICES = [
  ('rpi', 'Raspberry Pi'),
]

CODE_TEMPLATES = {
  '': {
    'title': 'Custom', 'icon': 'sliders',
    'desc': 'Specify a custom query',
    'code': ''
  },
  'random.value.asc': {
    'title': 'Random', 'icon': 'shuffle',
    'desc': 'Order items by random',
    'code': '''
      Item
        .annotate(rank=Model.Window(expression=Function.Rank(), order_by=Function.Random()))
    '''
  },
  'creation.value.desc': {
    'title': 'Creation date', 'icon': 'clock',
    'desc': 'Order items by creation date',
    'code': '''
      Item
        .annotate(rank=Model.Window(expression=Function.Rank(), order_by=Model.F('date_creation').desc()))
    '''
  },
  'creation.diff-today.desc': {
    'title': 'Week', 'icon': 'calendar-days',
    'desc': 'Order items by week relative to today',
    'code': '''
      Item
        .annotate(rank=Model.Window(expression=Function.Rank(), order_by=Function.Abs(
            Function.Extract('date_creation', 'week') -
            Function.Extract(Function.Now(), 'week')).desc()))
    '''
  },
}


class Frame(BaseModel):
    STR_FIELDS = BaseModel.STR_FIELDS + ["name"]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(
        max_length=255,
        verbose_name='Name', help_text='A name for this frame configuration.')
    description = models.TextField(
        verbose_name='Description', help_text='Provide a meaninful description.')
    enabled = models.BooleanField(
        verbose_name='Enabled')
    version = models.IntegerField(
        default=0,
        verbose_name='Update version', help_text='The version number increasing on each update')


class Source(BaseModel):
    STR_FIELDS = BaseModel.STR_FIELDS + ["name"]

    frame = models.ForeignKey(Frame, on_delete=models.CASCADE, related_name='sources')
    name = models.CharField(
        max_length=255,
        verbose_name='Name', help_text='Name describing the source')
    map_item_id_ext = models.CharField(
        max_length=32, blank=True,
        verbose_name='ID', help_text='Which field to map to item\'s ID (optional, can be used for an external reference)')
    map_item_url = models.CharField(
        max_length=32,
        verbose_name='URL', help_text='Which field to map to item\'s URL')
    map_item_date_creation = models.CharField(
        max_length=32, blank=True,
        verbose_name='Date', help_text='Which field to map to item\'s creation date')
    map_item_meta = models.TextField(
        default="",
        verbose_name='Additional fields', help_text='When more fields should be mapped add them line by line (format: "&lt;target-name&gt;=&lt;source-name&gt;\\n")')
    update_count = models.IntegerField(
        default=0,
        verbose_name='Update counter', help_text='Amount of update ran')
    update_date_start = models.DateTimeField(
        null=True,
        verbose_name='Start date of update', help_text='Date when the update process was started')
    update_date_end = models.DateTimeField(
        null=True,
        verbose_name='End date of update', help_text='Date when the update process finished')
    update_error = models.CharField(
        max_length=256, null=True,
        verbose_name='Update error', help_text='Which field to map to item\'s creation date')
    item_count_total = models.IntegerField(
        default=0,
        verbose_name='Total item count', help_text='Amount of items currently imported')
    item_count_error = models.IntegerField(
        default=0,
        verbose_name='Error item count', help_text='Amount of items failed to import')


class SourceStep(PluginModel):
    STR_FIELDS = PluginModel.STR_FIELDS + ["title", "instance", "data_in", "mime_in", "merge_in", "data_out", "mime_out", "loop_out"]

    CAT_NETWORK = 'network'
    CAT_DATA = 'data'

    source = models.ForeignKey(Source, on_delete=models.CASCADE, related_name='steps')
    ordering = models.IntegerField()
    title = models.CharField(
        max_length=255,
        verbose_name='Title', help_text='Short name of this step')
    description = models.CharField(
        max_length=255,
        verbose_name='Description', help_text='Description of this step')
    instance = models.CharField(
        max_length=255, blank=True,
        verbose_name='Instance', help_text='Same instances names will share same internal state')
    data_in = models.CharField(
        max_length=64, blank=True,
        verbose_name='Input', help_text='Use given file as input data')
    mime_in = models.CharField(
        max_length=64, choices=MIME_CHOICES, default='', blank=True,
        verbose_name='Input data type', help_text='Other then auto will override the type for input')
    merge_in = models.BooleanField(
        default=False,
        verbose_name='Merge multiple input results', help_text='Use multiple input result as one merged result')
    data_out = models.CharField(
        max_length=64, blank=True,
        verbose_name='Output', help_text='Save output data to given file')
    mime_out = models.CharField(
        max_length=64, choices=MIME_CHOICES, default='', blank=True,
        verbose_name='Output data type', help_text='Other then auto will override the type for output')
    loop_out = models.BooleanField(
        default=False,
        verbose_name='Iterate output results separately', help_text='Use results as one or iterate over the results data rows separately')

    class Meta:
        db_table = 'config_source_step'
        ordering = ['ordering']


class Item(BaseModel):
    STR_FIELDS = BaseModel.STR_FIELDS + ["url"]

    frame = models.ForeignKey(Frame, on_delete=models.CASCADE, related_name='items')
    source = models.ForeignKey(Source, on_delete=models.CASCADE, related_name='items')
    version = models.IntegerField(
        default=0,
        verbose_name='Update version', help_text='The version number increasing on each update')
    id_ext = models.CharField(
        max_length=255, null=True,
        verbose_name='External ID', help_text='Contains the external reference ID if available')
    url = models.CharField(
        max_length=1024,
        verbose_name='URL', help_text='The address to use to load the data of item')
    date_creation = models.DateTimeField(
        null=True,
        verbose_name='Date of creation', help_text='Date and time when the item was created')
    views = models.IntegerField(
        default=0,
        verbose_name='Views', help_text='Counter how often this item was shown')

    class Meta:
        ordering = ['-created']


class RankedItem(Item):
    STR_FIELDS = BaseModel.STR_FIELDS + ["rank"]

    rank = models.IntegerField(
        verbose_name='Rank', help_text='Calculated rank for this item')

    class Meta:
        managed = False


class ItemMeta(BaseModel):
    STR_FIELDS = BaseModel.STR_FIELDS + ["name", "value_text", "value_int", "value_date"]

    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='meta')
    name = models.CharField(
        max_length=128,
        verbose_name='Name', help_text='The name of the meta data field')
    value_text = models.CharField(
        max_length=255, null=True,
        verbose_name='Text value', help_text='Use this value to provide a text value (string)')
    value_int = models.IntegerField(
        null=True,
        verbose_name='Number value', help_text='Use this value to provide a number (integer)')
    value_date = models.DateTimeField(
        null=True,
        verbose_name='Date value', help_text='Use this value to provide a date')

    class Meta:
        db_table = 'config_item_meta'


class Sorting(PluginModel):
    STR_FIELDS = PluginModel.STR_FIELDS + ["title", "weight", "enabled"]

    CAT_CUSTOM = 'custom'
    CAT_DATE = 'date'

    frame = models.ForeignKey(Frame, on_delete=models.CASCADE, related_name='sortings')
    ordering = models.IntegerField()
    title = models.CharField(
        max_length=255,
        verbose_name='Title', help_text='Short name describing this sorting')
    weight = models.IntegerField(
        verbose_name='Weight', help_text='Specifies the weight and priority of sorting')
    enabled = models.BooleanField(
        verbose_name='Enabled')

    class Meta:
        db_table = 'config_sorting'
        ordering = ['-weight']


class Finishing(PluginModel):
    STR_FIELDS = PluginModel.STR_FIELDS + ["title", "image_in", "image_out", "enabled"]

    CAT_SHAPE = 'shape'
    CAT_TEXT = 'text'
    CAT_RESIZE = 'resize'
    CAT_TRANSFORM = 'transform'
    CAT_MERGE = 'merge'

    frame = models.ForeignKey(Frame, on_delete=models.CASCADE, related_name='finishings')
    ordering = models.IntegerField()
    title = models.CharField(
        max_length=255,
        verbose_name='Title', help_text='Short name describing finishing')
    image_in = models.CharField(
        max_length=64, blank=True, null=True,
        verbose_name='Image input', help_text='Name of image to modify (empty for default image)')
    image_out = models.CharField(
        max_length=64, blank=True, null=True,
        verbose_name='Image output', help_text='Name to output modified image (empty for default)')
    color_stroke = models.CharField(
        max_length=16,
        verbose_name='Foreground color', help_text='The foreground color (lines, text) to use in HEX (RGB)')
    color_fill = models.CharField(
        max_length=16, blank=True, null=True,
        verbose_name='Background color', help_text='The background color (fill) to use in HEX (RGB)')
    color_alpha = models.IntegerField(
        blank=True, null=True,
        verbose_name='Transparency', help_text='The alpha value between 0 (transparent) and 100 (no transparency)')
    stroke_width = models.IntegerField(
        blank=True, null=True,
        verbose_name='Line width', help_text='The width to use when drawing lines')
    enabled = models.BooleanField(
        verbose_name='Enabled')

    class Meta:
        db_table = 'config_finishing'
        ordering = ['ordering']

    def get_image_names_in(self):
        return re.split(r' |,', self.image_in)

    def get_image_names_out(self):
        return re.split(r' |,', self.image_out)


class Display(BaseModel):
    STR_FIELDS = BaseModel.STR_FIELDS + ["name"]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    frame = models.ForeignKey(Frame, on_delete=models.SET_NULL, blank=True, null=True)
    name = models.CharField(
        max_length=255,
        verbose_name='Name', help_text='A name for this display configuration.')
    description = models.TextField(
        verbose_name='Description', help_text='Provide a meaninful description.')
    enabled = models.BooleanField(
        verbose_name='Enabled')
    time_on = models.TimeField(
        blank=True, null=True,
        verbose_name='Switch on', help_text='Hour and minute to switch display on.')
    time_off = models.TimeField(
        blank=True, null=True,
        verbose_name='Switch off', help_text='Hour and minute to switch display off.')
    time_change = models.TimeField(
        blank=True, null=True,
        verbose_name='View', help_text='Hour and minutes to show each image.')
    device_type = models.CharField(
        max_length=32, blank=True, null=True, choices=DEVICE_CHOICES,
        verbose_name='Type', help_text='Type of display.')
    device_width = models.IntegerField(
        blank=True, null=True,
        verbose_name='Width', help_text='Display width in pixels.')
    device_height = models.IntegerField(
        blank=True, null=True,
        verbose_name='Height', help_text='Display height in pixels.')
    access_key = models.CharField(
        max_length=64, blank=True, null=True,
        verbose_name='Key', help_text='A secret access token to access data for display.')


