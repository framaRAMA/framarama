import logging

from django.db import connection
from django.db import connections

from framarama.base import utils
from frontend import models


logger = logging.getLogger(__name__)


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

    def _dump(self, cls, route):
        if route is None:
            return
        params = connections[route].get_connection_params()
        params = {name: value for name, value in params.items() if name in ['database', 'host', 'user']}
        cls = cls if type(cls) == type else type(cls)
        logger.debug("DB for \"{}\" routed to \"{}\" {}".format(cls.__name__, route, params));

    def _init(self):
        if DatabaseRouter.config is None:
            if 'frontend_config' not in connection.introspection.table_names():
                return False
            DatabaseRouter.config = utils.Config().get().get_config()
            if not DatabaseRouter.config:
                return False
        return True

    def _route(self, model):
        if model == models.Config:
            self._dump(model, 'default')
            return 'default'
        if not self._init():
            self._dump(model, 'default')
            return 'default'
        _config = DatabaseRouter.config
        if _config.mode == 'local' and _config.local_db_type == 'local':
            _routing = DatabaseRouter.routing['local']
        else:
            _routing = DatabaseRouter.routing['remote']
        _app_label = model._meta.app_label
        _route = _routing[_app_label] if _app_label in _routing else None
        self._dump(model, _route)
        return _route

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

