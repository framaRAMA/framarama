
from django.db import models


class BaseModel(models.Model):
    STR_FIELDS = ["id"]

    updated = models.DateTimeField(auto_now=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True

    def __str__(self):
        cls = type(self)
        fields = [field for field in self._meta.get_fields() if field.concrete and field.name in self.STR_FIELDS]
        return "<{}{}>".format(
             cls.__name__,
             ",".join([" {}={}".format(field, getattr(self, field)) for field in cls.STR_FIELDS])
        )


class PluginModel(BaseModel):
    STR_FIELDS = BaseModel.STR_FIELDS + ["plugin"]

    plugin = models.CharField(
        max_length=64)
    plugin_config = models.JSONField(
        blank=True, null=True, editable=False,
        verbose_name='Plugin config', help_text='Plugin settings in JSON structure')

    class Meta:
        abstract = True

