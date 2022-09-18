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

