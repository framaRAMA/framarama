
from django.db import models
from django.conf import settings

from framarama.base.models import JsonPropertiesModel


class SettingsQuerySet(models.QuerySet):

    def variables(self):
        return self.filter(category=Settings.CAT_USER_VARS)


class Settings(JsonPropertiesModel):
    STR_FIELDS = JsonPropertiesModel.STR_FIELDS + []

    CAT_INTERNAL = 'internal'
    CAT_USER_VARS = 'user.vars'

    objects = SettingsQuerySet.as_manager()

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name = models.CharField(
        max_length=255,
        verbose_name='Name', help_text='Name of group of settings')

    class Meta:
        db_table = 'config_settings'
        ordering = ['category', 'name']


