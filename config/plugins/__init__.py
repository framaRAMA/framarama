import pkgutil
import importlib
import config.plugins.sources
import config.plugins.sortings
import config.plugins.finishings
import config.plugins.contexts
import config.models as models


class Plugin:
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
        self._base_model = self._find_base_model(self.impl.Model)
        self._instances = {}

    def _find_base_model(self, cls):
        if Plugin._plugin_config_field in [_name for _name, _value in vars(cls).items()]:
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
            _fields = [_field.name for _field in self.impl.Model._meta.fields]
            _values.update({_n: _v for _n, _v in _plugin_config.items() if _n in _fields})
        _model = self.impl.Model(**_values)
        _model._base = instance
        return _model

    def load_model(self, identifier):
        return self.create_model(self._base_model.objects.filter(pk=identifier).get())

    def save_model(self, model):
        _values = model.get_field_values()
        _values[Plugin._plugin_config_field] = {}
        _model_fields = [_field.name for _field in model.get_fields()]
        for _name in [_name for _name in _values.keys() if _name in _model_fields]:
            _values[Plugin._plugin_config_field][_name] = _values.pop(_name)
        if model.id:
            _instance = self._base_model.objects.filter(pk=model.id).get()
            for _name, _value in _values.items():
                setattr(_instance, _name, _value)
        else:
            _instance = self._base_model(**_values)
        _instance.save()

    def delete_model(self, model):
        _instance = self._base_model.objects.filter(pk=model.id).get()
        _instance.delete();

    def get_create_form(self, *args, **kwargs):
        kwargs['instance'] = self.impl.Model()
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
                _module = importlib.import_module(_package)
                cls.instance._registry[_name] = Plugin(_name, _module);
        return cls.instance

    @classmethod
    def get(cls, name):
        _registry = cls._get_instance()._registry
        return _registry[name] if name in _registry else None

    @classmethod
    def all(cls):
        return cls._get_instance()._registry


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


class SortingPluginRegistry(PluginRegistry):

    @classmethod
    def _get_base_module(cls):
        return sortings


class FinishingPluginRegistry(PluginRegistry):

    @classmethod
    def _get_base_module(cls):
        return finishings


class ContextPluginRegistry(PluginRegistry):

    @classmethod
    def _get_base_module(cls):
        return contexts

