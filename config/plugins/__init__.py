import pkgutil
import logging
import collections

from rest_framework import serializers

from framarama.base import utils
from framarama.base.models import TreeManager
from config import models
from config.plugins import sources, sortings, finishings, contexts


logger = logging.getLogger(__name__)


class Plugin:
    _plugin_field = 'plugin'
    _plugin_config_field = 'plugin_config'
    _attrs_required = {
      'CAT': 'Implementation is missing category identifier (CAT)',
      'TITLE': 'Implementation is missing title (TITLE)',
      'DESCR': 'Implementation is missing description (DESCR)',
      'Model': 'Model class missing',
      'Form': 'Form class missing',
    }

    def __init__(self, name, module):
        if not hasattr(module, 'Implementation'):
            raise Exception("Can not import module " + name + ": Implementation missing")
        for _attr, _title in Plugin._attrs_required.items():
            if not hasattr(module.Implementation, _attr):
                raise Exception("Can not import module " + name + ": " + _title)
        self.name = name
        self.impl = module.Implementation
        self.cat = self.impl.CAT
        self.title = self.impl.TITLE
        self.descr = self.impl.DESCR
        self._model = self.impl.Model
        self._model_fields = [_field.name for _field in self._model().get_fields()]
        self._base_model = self._find_base_model(self._model)
        self._base_model_fields = [_field.name for _field in self._base_model().get_fields()]
        self._instances = {}

    def _find_base_model(self, cls):
        if Plugin._plugin_config_field in vars(cls).keys():
            return cls
        for _base_cls in cls.__bases__:
            _cls = self._find_base_model(_base_cls)
            if _cls:
                return _cls
        return None

    def base_model(self, identifier=None):
        return self._base_model() if identifier is None else self._base_model.objects.filter(pk=identifier).get()

    def create_model(self, instance=None):
        instance = instance if instance else self._model()
        if self.entangled():
            return instance
        _values = instance.get_field_values()
        _values[Plugin._plugin_field] = self.name
        _plugin_config = _values.pop(Plugin._plugin_config_field)
        if _plugin_config:
            _values.update({_n: _v for _n, _v in _plugin_config.items() if _n in self._model_fields})
        _model = self._model(**_values)
        _model._base = instance
        return _model

    def load_model(self, identifier):
        _base_model = self.base_model(identifier)
        if self.entangled():
            return _base_model
        return self.create_model(_base_model)

    def update_model(self, instance, values, base_values=False):
        _values = values.copy()
        _values[Plugin._plugin_field] = self.name
        if base_values:
            for _name in [_name for _name in values if _name not in self._base_model_fields]:
                del _values[_name]
            for _name in [_name for _name in values.get(Plugin._plugin_config_field, {}) if _name not in self._model_fields]:
                del _values[Plugin._plugin_config_field][_name]
        else:
            _values[Plugin._plugin_config_field] = {}
            for _name in [_name for _name in values.keys() if _name in self._model_fields]:
                _values[Plugin._plugin_config_field][_name] = values[_name]
        for _name in [_name for _name in _values.keys() if _name in self._base_model_fields]:
            setattr(instance, _name, _values[_name])

    def save_model(self, model, ordering, defaults=None, save=True, base_values=None):
        _values = {} if self.entangled() else model.get_field_values()
        _values.update(defaults.items() if defaults else {})
        _values[Plugin._plugin_field] = self.name
        _values['ordering'] = ordering
        if self.entangled():
            _instance = model
            for _k, _v in _values.items():
                setattr(_instance, _k, _v)
        else:
            _instance = self.base_model(model.id)
            self.update_model(_instance, _values, base_values if base_values != None else True if defaults else False)
        if save:
            _instance.save()
        return _instance

    def delete_model(self, model):
        if self.entangled():
            _instance = model
        else:
            _instance = self.base_model(model.id)
        _instance.delete();
        return _instance

    def get_form(self, *args, **kwargs):
        if 'instance' not in kwargs:
            kwargs['instance'] = self._model()
        return self.impl.Form(*args, **kwargs)

    def entangled(self):
        return hasattr(self.impl, 'Form')

    def run(self, *args, **kwargs):
        return self.run_instance('__default__', *args, **kwargs)

    def run_instance(self, instance, *args, **kwargs):
        if instance not in self._instances:
            self._instances[instance] = self.impl()
        return self._instances[instance].run(*args, **kwargs)


class PluginRegistry:
    EXPORT_JSON = 'json'
    EXPORT_JSON_PRETTY = 'json-pretty'
    EXPORT_DICT = 'dict'

    instance = None

    @classmethod
    def _get_base_module(cls):
        raise Exception('Plugin registry is missing the base module configuration')

    @classmethod
    def _get_instance(cls):
        if cls.instance is None:
            cls.instance = cls()
            cls.instance._registry = {}
            _base_module = cls.instance._get_base_module()
            _sub_modules = pkgutil.iter_modules(_base_module.__path__)
            for _name in [_submodule.name for _submodule in _sub_modules]:
                _package = _base_module.__name__ + '.' + _name
                _module = utils.Classes.load(_package)
                cls.instance._registry[_name] = Plugin(_name, _module);
        return cls.instance

    @classmethod
    def get(cls, name):
        _registry = cls._get_instance()._registry
        return _registry[name] if name in _registry else None

    @classmethod
    def get_enabled(cls, models):
        if len(models) == 0:
            return []
        if models[0]._meta.model.objects.is_tree():
            _models = []
            _depth_enabled = [True]
            for _model in models:
                _depth = _model.depth if _model.depth != None else 1
                if len(_depth_enabled) < _depth:    # lower items
                    _depth_enabled.append(_enabled)
                else:
                    while len(_depth_enabled) > _depth:  # upper level
                        _depth_enabled.pop()
                _enabled = _depth_enabled[-1] and _model.enabled
                if _enabled:
                    _models.append(_model)
        else:
            _models = [_model for _model in models if _model.enabled]
        return cls.get_all(_models)

    @classmethod
    def get_all(cls, models):
        _plugins = []
        for _model in models:
            _plugin = cls.get(_model.plugin)
            if not _plugin:
                logger.warn("Unknown {} plugin {} - skipping.".format(cls.__name__, _model.plugin))
                continue
            _plugins.append((_plugin, _plugin.create_model(_model)))
        return _plugins

    @classmethod
    def all(cls):
        return cls._get_instance()._registry

    @classmethod
    def export_config(cls, name, title, models, export=EXPORT_JSON, models_only=False):
        _models = models.for_export()
        _data = {
          'version': 1,
          'name': name,
          'title': title,
          'date': utils.DateTime.utc(utils.DateTime.now()),
          'data': cls.Serializer(_models, many=True).data
        }
        _result = _data['data'] if models_only else _data
        if export == PluginRegistry.EXPORT_JSON:
            return utils.Json.from_dict(_result)
        if export == PluginRegistry.EXPORT_JSON_PRETTY:
            return utils.Json.from_dict(_result, pretty=True)
        return _result

    @classmethod
    def import_config(cls, config, models, create_defaults):
        _import = collections.OrderedDict()
        for _id, _item in utils.Lists.from_tree(config, 'children', 'parent').items():
            _s = cls.Serializer(data=_item)
            if _s.is_valid():
                _import[_id] = _s.validated_data
            else:
                raise Exception("Can not convert item to {}: {}".format(cls.Serializer.Meta.model, _item))
        _models = models.for_import()
        _root_defaults = create_defaults.copy()
        _root_defaults['ordering'] = 0
        _root = models.get_root(_root_defaults) if models.is_tree() else None
        def _create_model(parent, ordering, path, item_dict):
            _plugin = cls.get(item_dict['plugin'])
            _plugin_model = _plugin.create_model()
            _model = _plugin.save_model(_plugin_model, ordering, {**create_defaults, **item_dict}, not _root)
            if _root:
                _node = _models[parent] if parent != '' else _root
                _node.refresh_from_db(fields=['lft', 'rgt', 'depth'])
                _node.add_child(instance=_model)
            _models[path] = _model
            return _model
        def _update_model(parent, ordering, path, item_dict, item_model):
            _plugin = cls.get(item_dict['plugin'])
            _model = item_model
            if _root:
                _model.refresh_from_db(fields=['lft', 'rgt', 'depth'])
            _plugin.save_model(_model, ordering, item_dict)
            _models[path] = _model
            return _model
        def _delete_model(parent, ordering, path, item_model):
            if _root:
                item_model.refresh_from_db(fields=['lft', 'rgt', 'depth'])
            _plugin = cls.get(item_model.plugin)
            _plugin.delete_model(item_model)
            for _k, _v in list(_models.items()):
                if _k.startswith(path):
                    del _models[_k]
            if _root:
                _node = _models[parent] if parent != '' else _root
                _node.refresh_from_db(fields=['lft', 'rgt', 'depth'])
            return item_model
        def wrap(mode, path, item, callback, *args):
            (_parent, _sep, _ordering) = path.rpartition('.')
            logger.debug("{}: {} - {}".format(mode, _parent, _ordering))
            _result[mode].append(callback(_parent, 0 if _root else _ordering, path, item, *args))
        [logger.debug("M: {} {}".format(i, _models[i])) for i in _models]
        [logger.debug("I: {} {}".format(i, _import[i])) for i in _import]
        _result = {'Create': [], 'Update': [], 'Delete': []}
        utils.Lists.process(
            _import.items(),
            lambda items: [(_idx, _models[_idx]) for _idx in items if _idx in _models],
            _models.items(),
            lambda items: [(_idx, _import[_idx]) for _idx in items if _idx in _import],
            create_func=lambda _idx, _item, *args: wrap('Create', _idx, _item, _create_model, *args),
            update_func=lambda _idx, _item, *args: wrap('Update', _idx, _item, _update_model, *args),
            delete_func=lambda _idx, _item, *args: wrap('Delete', _idx, _item, _delete_model, *args))
        logger.info('Import results:')
        for _type in ['Create', 'Update', 'Delete']:
            logger.info('{}:'.format(_type))
            [logger.info('- {}'.format(_item)) for _item in _result[_type]]


class PluginImplementation:

    def format_field(self, value, formatted=False, data_in=None):
        if formatted and data_in:
            return value.format(**data_in)
        return value

    def run(self, *args, **kwargs):
        raise Exception('Implementation missing')


class PluginImplementationSerializer(serializers.ModelSerializer):
    pass


class TreePluginImplementationSerializer(PluginImplementationSerializer):
    children = serializers.SerializerMethodField()

    def get_children(self, obj):
        return self.__class__(obj.get_children(), many=True).data


class SourcePluginRegistry(PluginRegistry):

    @classmethod
    def _get_base_module(cls):
        return sources


class SourcePluginImplementation(PluginImplementation):
    Model = models.SourceStep


class SortingPluginRegistry(PluginRegistry):

    @classmethod
    def _get_base_module(cls):
        return sortings


class SortingPluginImplementation(PluginImplementation):
    Model = models.Sorting


class FinishingPluginRegistry(PluginRegistry):

    class Serializer(TreePluginImplementationSerializer):
        class Meta:
            model = models.Finishing
            fields = ('title', 'enabled', 'image_in', 'image_out', 'plugin', 'plugin_config', 'children')

    @classmethod
    def _get_base_module(cls):
        return finishings


class FinishingPluginImplementation(PluginImplementation):
    Model = models.Finishing


class ContextPluginRegistry(PluginRegistry):

    @classmethod
    def _get_base_module(cls):
        return contexts


class ContextPluginImplementation(PluginImplementation):
    Model = models.FrameContext

    def get_images(self, ctx, names, default=True):
        _names = ['default'] if default else []
        _names.extend(names.split(' '))
        _images = {}
        for _name in _names:
            _image = ctx.get_image_data(_name)
            if _image:
                _images[_name] = _image
        return _images

