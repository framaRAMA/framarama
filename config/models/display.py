
from django.db import models
from django.conf import settings
from django.dispatch import receiver


from framarama.base.models import BaseModel, PluginModel, TreePluginModel, TreeManager, TreeQuerySet
from config.models import frame
from config.models.base import DisplayItemThumbnailData


DEVICE_CHOICES = [
  ('rpi', 'Raspberry Pi'),
]


class Display(BaseModel):
    STR_FIELDS = BaseModel.STR_FIELDS + ["name"]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    frame = models.ForeignKey(frame.Frame, on_delete=models.SET_NULL, blank=True, null=True)
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
        verbose_name='Uptime', help_text='The uptime of the device in seconds')
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
    app_uptime = models.BigIntegerField(
        blank=True, null=True,
        verbose_name='Application uptime', help_text='The uptime of the application in seconds')
    app_date = models.DateTimeField(
        blank=True, null=True,
        verbose_name='Application date', help_text='Date of current version in use')
    app_hash = models.CharField(
        max_length=48, blank=True, null=True,
        verbose_name='Application hash', help_text='Commit hash of current version in use')
    app_branch = models.CharField(
        max_length=64, blank=True, null=True,
        verbose_name='Application branch', help_text='Branch of current version in use')
    app_checked = models.DateTimeField(
        blank=True, null=True,
        verbose_name='Application update check', help_text='Date of last update check')
    app_installed = models.DateTimeField(
        blank=True, null=True,
        verbose_name='Application installation', help_text='Date of last update installation')

    class Meta:
        db_table = 'config_display_status'
        ordering = ['-created']


class DisplayItem(BaseModel):
    STR_FIELDS = BaseModel.STR_FIELDS + ["date_first_seen", "date_last_seen", "count_hit"]

    display = models.ForeignKey(Display, on_delete=models.CASCADE, related_name='items')
    item = models.ForeignKey(frame.Item, on_delete=models.CASCADE, related_name='display')
    date_first_seen = models.DateTimeField(
        blank=True, null=True,
        verbose_name='First seen', help_text='Date when the item was first shown on display')
    date_last_seen = models.DateTimeField(
        blank=True, null=True,
        verbose_name='Last seen', help_text='Date when the item was last shown on the display')
    duration_download = models.IntegerField(
        blank=True, null=True,
        verbose_name='Download duration', help_text='Duration in seconds used for downloading')
    duration_finishing = models.IntegerField(
        blank=True, null=True,
        verbose_name='Finishing duration', help_text='Duration in seconds used for finishing')
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
