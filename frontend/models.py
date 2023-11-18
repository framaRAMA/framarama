
from django.db import models

from framarama.base import utils
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
APP_UPDATE_CHECK_CHOICES = [
  (None, 'disabled'),
  (utils.DateTime.delta(0), 'use defaults'),
  (utils.DateTime.delta(days=1), 'daily'),
  (utils.DateTime.delta(days=7), 'weekly'),
  (utils.DateTime.delta(days=30), 'monthly'),
]
APP_UPDATE_INSTALL_HOUR_CHOICES = [
  (None, 'anytime'),
  (utils.DateTime.delta(hours=0), '00:00 - 01:59'),
  (utils.DateTime.delta(hours=2), '02:00 - 03:59'),
  (utils.DateTime.delta(hours=4), '04:00 - 05:59'),
  (utils.DateTime.delta(hours=6), '06:00 - 07:59'),
  (utils.DateTime.delta(hours=8), '08:00 - 09:59'),
  (utils.DateTime.delta(hours=10), '10:00 - 11:59'),
  (utils.DateTime.delta(hours=12), '12:00 - 13:59'),
  (utils.DateTime.delta(hours=14), '14:00 - 15:59'),
  (utils.DateTime.delta(hours=16), '16:00 - 17:59'),
  (utils.DateTime.delta(hours=18), '18:00 - 19:59'),
  (utils.DateTime.delta(hours=20), '20:00 - 21:59'),
  (utils.DateTime.delta(hours=22), '22:00 - 23:59'),
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

    app_update_check = models.DurationField(
        blank=True, null=True, choices=APP_UPDATE_CHECK_CHOICES,
        verbose_name='Update check', help_text='Time interval for update check')
    app_update_check_date = models.DateTimeField(
        null=True,
        verbose_name='Update check date', help_text='The date of the last update check')
    app_update_check_status = models.CharField(
        max_length=256, null=True,
        verbose_name='Update status', help_text='Status of last update check')
    app_update_install = models.BooleanField(
        default=False,
        verbose_name='Install updates')
    app_update_install_hour = models.DurationField(
        blank=True, null=True, choices=APP_UPDATE_INSTALL_HOUR_CHOICES,
        verbose_name='Install hour', help_text='Installation time range for updates')
    app_update_install_date = models.DateTimeField(
        null=True,
        verbose_name='Install updates date', help_text='The date of the last update install')
    app_update_install_status = models.CharField(
        max_length=256, null=True,
        verbose_name='Install update status', help_text='Status of last update install')

