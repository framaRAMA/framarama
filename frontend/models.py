
from django.db import models

from framarama.base.models import BaseModel, TIMEZONE_CHOICES


MODE_CHOICES = [
  ('local', 'Local setup'),
  ('cloud', 'Cloud setup'),
]
STATUS_RESTRICTION_CHOICES = [
  ('sys', 'System (like uptime)'),
  ('memory', 'Memory (usage and free)'),
  ('cpu', 'CPU (device load)'),
  ('disk', 'Disk (usage and free)'),
  ('network', 'Network (status and connectivty)'),
  ('screen', 'Display (status and geometry)'),
  ('item', 'Item (views, counts, hits)'),
  ('app', 'Application (release and version)'),
  ('thumbs', 'Thumbnails (media thumbnails)'),
]
DBTYPE_CHOICES = [
  ('local', 'Integrated database (no database config required)'),
  ('mysql', 'MySQL/MariaDB server')
]
WATERMARKTYPE_CHOICES = [
  ('none', 'Do not watermark items'),
  ('ribbon', 'Show ribbon at the corners'),
  ('hbars', 'Draw horizontal bars (top & botton)'),
  ('vbars', 'Draw vertical bars (left & right)'),
]


class Config(BaseModel):
    STR_FIELDS = BaseModel.STR_FIELDS

    sys_time_zone = models.CharField(
        max_length=32, choices=TIMEZONE_CHOICES, blank=True, null=True,
        verbose_name='Timezone', help_text='The timezone to use for this device')

    mode = models.CharField(
        max_length=32, choices=MODE_CHOICES,
        verbose_name='Mode', help_text='Setup mode for frontend')
    local_db_type = models.CharField(
        max_length=16, choices=DBTYPE_CHOICES, blank=True, null=True,
        verbose_name='Database type', help_text='Select type of database')
    local_db_host = models.CharField(
        max_length=64, blank=True, null=True,
        verbose_name='Database server', help_text='Use external database server instead of local one')
    local_db_name = models.CharField(
        max_length=64, blank=True, null=True,
        verbose_name='Database name', help_text='Put tables into the existing database')
    local_db_user = models.CharField(
        max_length=64, blank=True, null=True,
        verbose_name='Database user', help_text='Use this username when connecting to database')
    local_db_pass = models.CharField(
        max_length=64, blank=True, null=True,
        verbose_name='Database password', help_text='The password for the database user')
    cloud_server = models.CharField(
        max_length=255,
        verbose_name='Server', help_text='Remote server URL')
    cloud_display_access_key = models.CharField(
        max_length=64, blank=True, null=True,
        verbose_name='Display', help_text='Access key for display')
    cloud_status_restriction = models.JSONField(
        max_length=64, blank=True, null=True,
        verbose_name='Status reporting', help_text='Define which status information will be submitted to server')

    date_app_startup = models.DateTimeField(
        null=True,
        verbose_name='Startup', help_text='Startup date of the system')
    date_items_update = models.DateTimeField(
        null=True,
        verbose_name='Items update', help_text='The date when the list of items was updates the last time')
    count_items = models.IntegerField(
        default=0,
        verbose_name='Item count', help_text='Total amount of item currently in collection')
    count_views = models.IntegerField(
        default=0,
        verbose_name='Views', help_text='Total count of images shown on display')
    count_errors = models.IntegerField(
        default=0,
        verbose_name='Errors', help_text='Count of errors on image processing')
    count_items_keep = models.IntegerField(
        blank=True, null=True,
        verbose_name='Keep items', help_text='Amount of item to keep and show preview in frontend (default 6)')

    watermark_type = models.CharField(
        max_length=32,default='ribbon', choices=WATERMARKTYPE_CHOICES,
        verbose_name='Watermark type', help_text='Amount of item to keep and show preview in frontend')
    watermark_shift = models.IntegerField(
        blank=True, null=True,
        verbose_name='Watermark shift', help_text='Amount to move water mark away from borders (default 10)')
    watermark_scale = models.IntegerField(
        blank=True, null=True,
        verbose_name='Watermark scale', help_text='Make watermark larger or smaller (default 2)')

