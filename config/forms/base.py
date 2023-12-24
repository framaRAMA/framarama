import sys

from framarama.base import forms as base


class BasePluginForm(base.BaseModelForm):
    dependencies = {}
    
    def _field_groups(self, fields):
        impl = sys.modules[self.__module__].Implementation
        _groups = {
            'default': {
                'title': 'General settings',
                'fields': fields,
            },
            'plugin': {
                'title': 'Plugin settings: ' + impl.TITLE + ' - ' + impl.DESCR,
                'fields': [field for field in self.fields.keys() if field not in fields],
            }
        }
        return _groups

    def field_dependencies(self):
        return self.dependencies

    def save(self, plugin, defaults=None, *args, **kwargs):
        _commit = kwargs.get('commit', True)
        _plugin_model = super().save(commit=False, *args, **kwargs)
        _plugin_model.name = plugin.name
        for _name, _value in defaults.items() if defaults else {}:
            setattr(_plugin_model, _name, _value)
        _base_model = plugin.save_model(_plugin_model, _commit)
        return _base_model

