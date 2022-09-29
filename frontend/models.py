from django.db import models

from framarama.base.models import BaseModel


MODE_CHOICES = [
  ('local', 'Local setup'),
  ('cloud', 'Cloud setup'),
]
DBTYPE_CHOICES = [
  ('local', 'Integrated database (no database config required)'),
  ('mysql', 'MySQL/MariaDB server')
]


class Config(BaseModel):
    STR_FIELDS = BaseModel.STR_FIELDS

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
        verbose_name='Server', help_text='Remove server URL')
    cloud_display_access_key = models.CharField(
        max_length=64, blank=True, null=True,
        verbose_name='Display', help_text='Access key for display')


