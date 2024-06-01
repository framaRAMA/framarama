import re

from django.db import models
from django.conf import settings
from django.dispatch import receiver


from framarama.base import utils
from framarama.base.models import BaseModel, PluginModel, TreePluginModel, TreeManager, TreeQuerySet
from config.models.base import Data, ItemThumbnailData


MIME_CHOICES = [
  ('', 'Auto (automatically detect mime type)'),
  ('text/csv', 'CSV (comma separated data)'),
  ('application/json', 'JSON'),
  ('text/plain', 'Plain text'),
]

SOURCE_UPDATE_INTERVAL_CHOICES = [
  (None, 'no automatic update'),
  (utils.DateTime.delta(0), 'use defaults'),
  (utils.DateTime.delta(minutes=15), 'each 15 minutes'),
  (utils.DateTime.delta(hours=1), 'each hour'),
  (utils.DateTime.delta(days=1), 'once a day'),
]


class Frame(BaseModel):
    STR_FIELDS = BaseModel.STR_FIELDS + ["name"]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
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

    def get_last_update(self):
        _max = self.sources.aggregate(models.Max('update_date_start'))
        return _max['update_date_start__max'] if _max else None


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
        default="", blank=True,
        verbose_name='Additional fields', help_text='When more fields should be mapped add them line by line (format: "&lt;target-name&gt;=&lt;source-name&gt;\\n")')
    update_interval = models.DurationField(
        blank=True, null=True, choices=SOURCE_UPDATE_INTERVAL_CHOICES,
        verbose_name='Update interval', help_text='Time interval to run an automatic update of items')
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
        verbose_name='Update error', help_text='Errors of last update process')
    update_status = models.CharField(
        max_length=256, null=True,
        verbose_name='Update status', help_text='Result status information of last update process')
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
    thumbnail = models.OneToOneField(ItemThumbnailData, null=True, on_delete=models.SET_NULL)

    class Meta:
        ordering = ['-created']


@receiver(models.signals.post_delete, sender=Item)
def post_delete_item(sender, instance, *args, **kwargs):
    Data.post_delete(sender, instance, instance.thumbnail, *args, **kwargs)


class RankedItem(Item):
    STR_FIELDS = BaseModel.STR_FIELDS + ["rank"]

    item_ptr = models.OneToOneField(Item, on_delete=models.DO_NOTHING, parent_link=True, primary_key=True)
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


class Finishing(TreePluginModel):
    STR_FIELDS = PluginModel.STR_FIELDS + ["title", "image_in", "image_out", "enabled"]

    CAT_GROUP = 'group'
    CAT_SHAPE = 'shape'
    CAT_TEXT = 'text'
    CAT_RESIZE = 'resize'
    CAT_TRANSFORM = 'transform'
    CAT_MERGE = 'merge'
    CAT_IMAGE = 'image'

    objects = TreeManager.from_queryset(TreeQuerySet)().prefetch(['frame'])

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
    enabled = models.BooleanField(
        verbose_name='Enabled')

    class Meta:
        db_table = 'config_finishing'
        ordering = ['ordering']

    def get_image_names_in(self, default=None):
        return re.split(r' |,', self.image_in) if self.image_in else default

    def get_image_names_out(self, default=None):
        return re.split(r' |,', self.image_out) if self.image_out else default


class FrameContext(PluginModel):
    STR_FIELDS = PluginModel.STR_FIELDS + ["name", "enabled"]

    CAT_EXIF = 'exif'
    CAT_GEO = 'geo'
    CAT_VARS = 'vars'

    frame = models.ForeignKey(Frame, on_delete=models.CASCADE, related_name='contexts')
    ordering = models.IntegerField()
    name = models.CharField(
        max_length=255,
        verbose_name='Name', help_text='Name to access the context data (use lowercase and single word)')
    enabled = models.BooleanField(
        verbose_name='Enabled')

    class Meta:
        db_table = 'config_frame_context'
        ordering = ['ordering']
