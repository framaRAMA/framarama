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

    def save(self, plugin, defaults=None, models=None, *args, **kwargs):
        _commit = kwargs.pop('commit', True)
        _plugin_model = super().save(commit=False, *args, **kwargs)
        return plugin.save_model(_plugin_model, models.count() if models else 0, defaults, _commit)


class TreeBasePluginForm(BasePluginForm):

    def save(self, plugin, defaults, root_defaults, models, *args, **kwargs):
        _commit = kwargs.pop('commit', False)
        _base_model = super().save(plugin, defaults, None, commit=_commit, *args, **kwargs)
        return models.get_root(root_defaults).add_child(instance=_base_model)

