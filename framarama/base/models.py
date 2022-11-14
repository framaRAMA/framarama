
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

    def get_field(self, name):
        _fields = [_field for _field in self.get_fields(True) if _field.name == name]
        return _fields.pop(0) if _fields else None

    def get_fields(self, base=False, model=True):
        if base and model:
            _fields = self._meta.fields
        elif model:
            _fields = self._meta.get_fields(include_parents=False)
        else:
            _model = [_field.name for _field in self._meta.get_fields(include_parents=False)]
            _all = self._meta.fields
            _fields = [_field for _field in _all if _field.name not in _model]
        _fields = [_field for _field in _fields if not _field.name.endswith('_ptr')]
        return _fields

    def get_field_values(self):
        return {_field.name:getattr(self, _field.name) for _field in self.get_fields(True)}

