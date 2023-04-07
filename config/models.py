import io
import os
import re
import hashlib
import logging

from django.db import models
from django.conf import settings
from django.core.files.base import File
from django.dispatch import receiver

from framarama.base import utils
from framarama.base.models import BaseModel, PluginModel


logger = logging.getLogger(__name__)


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

SOURCE_UPDATE_INTERVAL_CHOICES = [
  (None, 'no automatic update'),
  (utils.DateTime.delta(0), 'use defaults'),
  (utils.DateTime.delta(minutes=15), 'each 15 minutes'),
  (utils.DateTime.delta(hours=1), 'each hour'),
  (utils.DateTime.delta(days=1), 'once a day'),
]


class Data(BaseModel):
    STR_FIELDS = BaseModel.STR_FIELDS + ['category', 'data_file']

    def _upload(instance, path):
        _md5 = hashlib.md5()
        _md5.update("{}#{}".format(path, utils.DateTime.now().timestamp()).encode())
        _md5_hex = _md5.hexdigest()
        _storage_path = [settings.FRAMARAMA['DATA_PATH'], 'config']
        _storage_path.extend(instance.storage_path())
        _storage_path.extend([_md5_hex[0:2], _md5_hex[2:4], _md5_hex])
        return os.path.join(*_storage_path)

    category = models.CharField(
        max_length=255,
        verbose_name='Category', help_text='The category of the type of data item')
    data_size = models.IntegerField(
        blank=True, null=True,
        verbose_name='Size', help_text='Amount of bytes used for this data item')
    data_mime = models.CharField(
        max_length=64, blank=True, null=True,
        verbose_name='Mime type', help_text='The content type of this data item')
    data_file = models.FileField(
        blank=True, null=True, editable=False, upload_to=_upload,
        verbose_name='Save as file', help_text='Store content in the filesystem')
    meta = models.JSONField(
        blank=True, null=True, editable=False, default=dict,
        verbose_name='Info', help_text='Meta information for data item')

    def storage_path(self):
        return []

    def update(self, existing):
        existing.data_mime = self.data_mime
        existing.data_size = self.data_file.size
        existing.meta = self.meta
        existing.data_file.open('wb')
        existing.data_file.write(self.data_file.read())
        existing.data_file.close()

    def set_meta(self, name, value):
        self.meta[name] = value

    def get_meta(self, name):
        self.meta.get(name, None)

    def data(self):
        try:
            return utils.Filesystem.file_read(self.data_file.path)
        except FileNotFoundError as e:
            logger.error("Can not load data file for {}: {}".format(self, e))
        return None

    def delete(self, *args, **kwargs):
        if self.data_file:
            self.data_file.delete()
        super(Data, self).delete(*args, **kwargs)

    @classmethod
    def create(cls, json=None, data=None, mime=None, meta=None):
        if json:
            _data = utils.Json.from_dict(json).encode()
            _mime = 'application/json' if mime is None else mime
        elif data:
            _data = data
        else:
            raise Exception('Specify JSON or data to create a Data object')
        _file = File(io.BytesIO(_data), name='display_item_thumbnail')
        _instance = cls()
        _instance.data_mime = mime
        _instance.data_size = _file.size
        _instance.data_file = _file
        _instance.meta = meta if meta else {}
        return _instance

    @classmethod
    def post_delete(cls, sender, instance, entity, *args, **kwargs):
        logger.debug("Delete from {} for {}: {}".format(sender, instance, entity))
        if entity:
            entity.delete()


class BaseImageData(Data):

    class Meta:
        proxy = True

    def get_width(self):
        return self.get_meta('width')

    def set_width(self, width):
        return self.set_meta('width', width)

    def get_height(self):
        return self.get_meta('height')

    def set_width(self, height):
        return self.set_meta('height', height)


class ItemThumbnailData(BaseImageData):

    class Meta:
        proxy = True

    def storage_path(self):
        return ['item', 'thumbnail']


class DisplayItemThumbnailData(BaseImageData):

    class Meta:
        proxy = True

    def storage_path(self):
        return ['display', 'thumbnail']


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


class Finishing(PluginModel):
    STR_FIELDS = PluginModel.STR_FIELDS + ["title", "image_in", "image_out", "enabled"]

    CAT_SHAPE = 'shape'
    CAT_TEXT = 'text'
    CAT_RESIZE = 'resize'
    CAT_TRANSFORM = 'transform'
    CAT_MERGE = 'merge'
    CAT_IMAGE = 'image'

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


class Display(BaseModel):
    STR_FIELDS = BaseModel.STR_FIELDS + ["name"]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
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

    def get_latest_status(self, count=None):
        _latest = self.status.order_by('id').reverse()
        return _latest.first() if count is None else _latest[:count]

    def get_latest_items(self, count=None):
        _latest = self.items.order_by('date_last_seen').reverse()
        return _latest.first() if count is None else _latest[:count]

    def get_top_items(self, count=None):
        _latest = self.items.order_by('count_hit').reverse()
        return _latest.first() if count is None else _latest[:count]

    def get_newest_items(self, count=None):
        _newest = self.items.order_by('created').reverse()
        return _newest.first() if count is None else _newest[:count]


class DisplayStatus(BaseModel):
    STR_FIELDS = BaseModel.STR_FIELDS + ["uptime", "memory_free", "cpu_load", "cpu_temp", "disk_data_free", "disk_tmp_free", "screen_on", "items_total"]

    display = models.ForeignKey(Display, on_delete=models.CASCADE, related_name='status')
    uptime = models.BigIntegerField(
        blank=True, null=True,
        verbose_name='Update', help_text='The uptime of the device in milli seconds')
    memory_used = models.BigIntegerField(
        blank=True, null=True,
        verbose_name='Memory used', help_text='Amount of memory currently in use')
    memory_free = models.BigIntegerField(
        blank=True, null=True,
        verbose_name='Memory available', help_text='Amount of memory currently available')
    cpu_load = models.FloatField(
        blank=True, null=True,
        verbose_name='CPU load', help_text='Current load of CPU')
    cpu_temp = models.IntegerField(
        blank=True, null=True,
        verbose_name='CPU temperature', help_text='Current temperature of CPU')
    disk_data_free = models.BigIntegerField(
        blank=True, null=True,
        verbose_name='Disk DATA free', help_text='Available amount of space in data partition')
    disk_tmp_free = models.BigIntegerField(
        blank=True, null=True,
        verbose_name='Disk TMP free', help_text='Available amount of space in temporary partition')
    network_profile = models.CharField(
        max_length=32, blank=True, null=True,
        verbose_name='Network profile', help_text='The name of the network profile currently in use')
    network_connected = models.DateTimeField(
        blank=True, null=True,
        verbose_name='Network connected', help_text='Time when the network connection was established')
    network_address_ip = models.CharField(
        max_length=64, blank=True, null=True,
        verbose_name='Network device IP', help_text='The network address of device')
    network_address_gateway = models.CharField(
        max_length=64, blank=True, null=True,
        verbose_name='Network gateway IP', help_text='The network address of gateway')
    screen_on = models.BooleanField(
        blank=True, null=True,
        verbose_name='Screen status', help_text='Status of screen (1 is on, 0 is off)')
    screen_width = models.IntegerField(
        blank=True, null=True,
        verbose_name='Screen width', help_text='The actual width of screen in pixels')
    screen_height = models.IntegerField(
        blank=True, null=True,
        verbose_name='Screen height', help_text='The actual height of screen in pixels')
    items_total = models.IntegerField(
        blank=True, null=True,
        verbose_name='Items total', help_text='Total amount of items currently in use')
    items_shown = models.IntegerField(
        blank=True, null=True,
        verbose_name='Items shown', help_text='Total amount of items shown')
    items_error = models.IntegerField(
        blank=True, null=True,
        verbose_name='Items error', help_text='Total amount of items with errors')
    items_updated = models.DateTimeField(
        blank=True, null=True,
        verbose_name='Items updated', help_text='Time of the last item list update')
    app_date = models.DateTimeField(
        blank=True, null=True,
        verbose_name='Application date', help_text='Date of current version in use')
    app_hash = models.CharField(
        max_length=48, blank=True, null=True,
        verbose_name='Application hash', help_text='Commit hash of current version in use')
    app_branch = models.CharField(
        max_length=64, blank=True, null=True,
        verbose_name='Application branch', help_text='Branch of current version in use')

    class Meta:
        db_table = 'config_display_status'
        ordering = ['-created']


class DisplayItem(BaseModel):
    STR_FIELDS = BaseModel.STR_FIELDS + ["date_first_seen", "date_last_seen", "count_hit"]

    display = models.ForeignKey(Display, on_delete=models.CASCADE, related_name='items')
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='display')
    date_first_seen = models.DateTimeField(
        blank=True, null=True,
        verbose_name='First seen', help_text='Date when the item was first shown on display')
    date_last_seen = models.DateTimeField(
        blank=True, null=True,
        verbose_name='Last seen', help_text='Date when the item was last shown on the display')
    count_hit = models.IntegerField(
        blank=True, null=True,
        verbose_name='Hits', help_text='Amount of hits for this item')
    thumbnail = models.OneToOneField(DisplayItemThumbnailData, null=True, on_delete=models.SET_NULL)

    class Meta:
        db_table = 'config_display_item'
        ordering = ['-created']


@receiver(models.signals.post_delete, sender=DisplayItem)
def post_delete_display_item(sender, instance, *args, **kwargs):
    Data.post_delete(sender, instance, instance.thumbnail, *args, **kwargs)
