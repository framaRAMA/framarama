import pkgutil
import logging

from framarama.base import utils
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
      'CreateForm': 'CreateForm class missing',
      'UpdateForm': 'UpdateForm class missing',
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

    def create_model(self, instance):
        _values = instance.get_field_values()
        _plugin_config = _values.pop(Plugin._plugin_config_field)
        if _plugin_config:
            _values.update({_n: _v for _n, _v in _plugin_config.items() if _n in self._model_fields})
        _model = self._model(**_values)
        _model._base = instance
        return _model

    def load_model(self, identifier):
        return self.create_model(self._base_model.objects.filter(pk=identifier).get())

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

    def save_model(self, model):
        _values = model.get_field_values()
        if model.id:
            _instance = self._base_model.objects.filter(pk=model.id).get()
        else:
            _instance = self._base_model()
        self.update_model(_instance, _values)
        _instance.save()

    def delete_model(self, model):
        _instance = self._base_model.objects.filter(pk=model.id).get()
        _instance.delete();

    def get_create_form(self, *args, **kwargs):
        kwargs['instance'] = self._model()
        return self.impl.CreateForm(*args, **kwargs)

    def get_update_form(self, *args, **kwargs):
        return self.impl.UpdateForm(*args, **kwargs)

    def run(self, *args, **kwargs):
        return self.run_instance('__default__', *args, **kwargs)

    def run_instance(self, instance, *args, **kwargs):
        if instance not in self._instances:
            self._instances[instance] = self.impl()
        return self._instances[instance].run(*args, **kwargs)


class PluginRegistry:
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
        return cls.get_all([_model for _model in models if _model.enabled])

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
    def export_config(cls, name, title, serializer, models):
        return utils.Json.from_dict({
          'version': 1,
          'name': name,
          'title': title,
          'date': utils.DateTime.utc(utils.DateTime.now()),
          'data': serializer(models, many=True).data
        })


class PluginImplementation:

    def format_field(self, value, formatted=False, data_in=None):
        if formatted and data_in:
            return value.format(**data_in)
        return value

    def run(self, *args, **kwargs):
        raise Exception('Implementation missing')



class SourcePluginRegistry(PluginRegistry):

    @classmethod
    def _get_base_module(cls):
        return sources


class SourcePluginImplementation(PluginImplementation):
    pass


class SortingPluginRegistry(PluginRegistry):

    @classmethod
    def _get_base_module(cls):
        return sortings


class SortingPluginImplementation(PluginImplementation):
    pass


class FinishingPluginRegistry(PluginRegistry):

    @classmethod
    def _get_base_module(cls):
        return finishings


class FinishingPluginImplementation(PluginImplementation):
    pass


class ContextPluginRegistry(PluginRegistry):

    @classmethod
    def _get_base_module(cls):
        return contexts


class ContextPluginImplementation(PluginImplementation):

    def get_images(self, ctx, names, default=True):
        _names = ['default'] if default else []
        _names.extend(names.split(' '))
        _images = {}
        for _name in _names:
            _image = ctx.get_image_data(_name)
            if _image:
                _images[_name] = _image
        return _images

