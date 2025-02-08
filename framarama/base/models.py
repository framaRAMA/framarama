import zoneinfo

from django.db import models

from treebeard.ns_tree import NS_Node, NS_NodeManager, NS_NodeQuerySet

from framarama.base import utils


TIMEZONE_CHOICES = [(None, '(default)')]
TIMEZONE_CHOICES.extend([(_tz, _tz) for _tz in sorted(zoneinfo.available_timezones())])


class BaseQuerySet(models.QuerySet):

    def is_tree(self):
        return False

    def for_export(self):
        return self

    def for_import(self):
        return {_i: _model for _i, _model in self.items()}


class BaseManager(models.Manager):

    def get_queryset(self):
        return BaseQuerySet(self.model, using=self._db)


class TreeQuerySet(NS_NodeQuerySet):

    def is_tree(self):
        return True

    def for_export(self, all=False):
        return self.filter(depth__gt=1) if all else self.filter(depth=2)

    def for_import(self):
        return utils.Lists.from_annotated(self.annotated())

    def annotated(self):
        return self.model.get_annotated_list_qs(self.for_export(True))

    def roots(self):
        return self.filter(lft=1)

    def get_root(self, create_defaults=None):
        _root = self.roots().first()
        if not _root and create_defaults:
            _root_node = create_defaults.copy()
            _root_node['title'] = 'ROOT'
            _root = self.add_root(**_root_node)
        return _root

    def add_root(self, **kwargs):
        return self.model.add_root(**kwargs)


class TreeManager(NS_NodeManager):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._prefetch = []

    def prefetch(self, prefetch):
        self._prefetch = prefetch
        return self

    def get_queryset(self):
        return TreeQuerySet(self.model, using=self._db).order_by('tree_id', 'lft').prefetch_related(*self._prefetch)


class BaseModel(models.Model):
    STR_FIELDS = ["id"]

    updated = models.DateTimeField(auto_now=True)
    created = models.DateTimeField(auto_now_add=True)

    objects = BaseManager.from_queryset(BaseQuerySet)()

    class Meta:
        abstract = True

    def __str__(self):
        cls = type(self)
        fields = [field for field in self._meta.get_fields() if field.concrete and field.name in self.STR_FIELDS]
        return "<{}{}>".format(
             cls.__name__,
             ",".join([" {}={}".format(field, getattr(self, field)) for field in cls.STR_FIELDS])
        )


class JsonPropertiesModel(BaseModel):
    STR_FIELDS = BaseModel.STR_FIELDS + ["properties"]

    category = models.CharField(
        max_length=64)
    properties = models.JSONField(
        blank=True, null=True, editable=True, default=dict,
        verbose_name='List of properties', help_text='All properties as key/value pairs in JSON structure')

    class Meta:
        abstract = True


class PluginModel(BaseModel):
    STR_FIELDS = BaseModel.STR_FIELDS + ["plugin"]

    plugin = models.CharField(
        max_length=64)
    plugin_config = models.JSONField(
        blank=True, null=True, editable=True, default=dict,
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
        return {_field.name:getattr(self, _field.name, None) for _field in self.get_fields(True)}

    def get_config(self):
        _config = self.get_field_values()
        _plugin_config = _config.pop('plugin_config')
        if _plugin_config:
            _config.update(_plugin_config)
        return _config


class TreePluginModel(PluginModel, NS_Node):

    objects = TreeManager.from_queryset(TreeQuerySet)()

    class Meta:
        abstract = True
