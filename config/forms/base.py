import sys

from framarama.base import forms as base


class BasePluginForm(base.BaseModelForm):
    dependencies = {}
    
    def field_groups(self):
        _impl = sys.modules[self.__module__].Implementation
        _model_fields = [_field.name for _field in self.Meta.model._meta.get_fields(include_parents=False)]
        _plugin_fields = self.Meta.fields
        return {
            'default': {
                'title': 'General settings',
                'fields': [_name for _name in _plugin_fields if _name not in _model_fields],
            },
            'plugin': {
                'title': 'Plugin settings: ' + _impl.TITLE + ' - ' + _impl.DESCR,
                'fields': [field for field in _plugin_fields if field in _model_fields],
            }
        }

    def field_dependencies(self):
        return self.dependencies

    def save(self, plugin, defaults=None, models=None, base_values=None, *args, **kwargs):
        _commit = kwargs.pop('commit', True)
        _plugin_model = super().save(commit=False, *args, **kwargs)
        return plugin.save_model(_plugin_model, models.count() if models else 0, defaults, _commit, base_values)


class TreeBasePluginForm(BasePluginForm):

    def save(self, plugin, defaults, models, base_values=None, *args, **kwargs):
        _commit = kwargs.pop('commit', False)
        _base_model = super().save(plugin, defaults, None, commit=_commit, base_values=base_values, *args, **kwargs)
        _root_defaults = defaults.copy()
        _root_defaults['ordering'] = 0
        return models.get_root(_root_defaults).add_child(instance=_base_model)

