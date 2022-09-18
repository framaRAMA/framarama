from django.db import connection

from framarama.base import utils
from frontend import models


class DatabaseRouter:
    routing = {
        'local': {
            'auth': 'default',
            'sessions': 'default',
            'api': 'default',
            'config': 'default',
            'frontend': 'default'
        },
        'remote': {
            'auth': 'config',
            'sessions': 'config',
            'api': 'config',
            'config': 'config',
            'frontend': 'default'
        }
    }
    config = None

    def _init(self):
        if DatabaseRouter.config is None:
            if 'frontend_config' not in connection.introspection.table_names():
                return False
            DatabaseRouter.config = utils.Config().get_config()
            if not DatabaseRouter.config:
                return False
        return True

    def _route(self, model):
        if model == models.Config:
            return 'default'
        if not self._init():
            return 'default'
        _config = DatabaseRouter.config
        if _config.mode == 'local' and _config.local_db_type == 'local':
            _routing = DatabaseRouter.routing['local']
        else:
            _routing = DatabaseRouter.routing['remote']
        _app_label = model._meta.app_label
        return _routing[_app_label] if _app_label in _routing else None

    def db_for_read(self, model, **hints):
        return self._route(model)

    def db_for_write(self, model, **hints):
        return self._route(model)

    def allow_relation(self, obj1, obj2, **hints):
        _route1 = self._route(obj1)
        _route2 = self._route(obj2)
        if _route1 and _route2 and _route1 == _route2:
            return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label in self.routing:
            return db == self.routing[app_label]
        return None

