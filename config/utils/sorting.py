import re
import random

from django.db import models as Model
from django.db.models import functions as Function

from config.plugins import SortingPluginRegistry


class Context:

    def __init__(self, frame, random_item=False):
        self._frame = frame
        self._random_item = random_item
        self._data = {'Item': self._frame.items.order_by(), 'Model': Model, 'Function': Function}
    
    def get_frame(self):
        return self._frame

    def get_random_item(self):
        return self._random_item
    
    def get_data(self):
        return self._data


class Processor:

    def __init__(self, context):
        self._context = context
        self._instances = {}

    def get_plugin(self, plugin_name):
        return SortingPluginRegistry.get(plugin_name)

    def get_model(self, sorting):
        return self.get_plugin(sorting.plugin).load_model(sorting.id)

    def process(self):
        '''
Database shell imports for testing queries:
from django.db.models import functions as Function
from django.db import models as Model
from config import models
Item = models.Item.objects
        '''
        _result = {'errors':{}}
        _queries = []
        _data = self._context.get_data()
        for _sorting in self._context.get_frame().sortings.all():
            if not _sorting.enabled:
                continue
            _plugin = self.get_plugin(_sorting.plugin)
            _sorting = self.get_model(_sorting)

            _code = _plugin.run(_sorting, self._context)
            _code = re.sub(r"[\r\n]+\s*", "", _code)  # fix indent by removing newline/whitespaces
            try:
                _code = _code + ".annotate(rank=Model.F('rank')*Model.Value({}))".format(_sorting.weight)
                _code = _code + ".values('id', 'rank')"
                _queries.append(eval(_code, _data))
            except Exception as e:
                _result['errors']['sorting{}'.format(_sorting.id)] = e

        if len(_queries) == 0:
            _query = _data['Item'].order_by('id').annotate(rank=Model.F('id'))
        else:
            _query = _queries.pop(0)
            if len(_queries):
                _query = _query.union(*_queries)

        # Get raw SQL query using compiler as used in the Query code, but
        # tis defaults to "default" connection and not "config" connection:
        # https://github.com/django/django/blob/6654289f5b350dfca3dc4f6abab777459b906756/django/db/models/sql/query.py#L293
        (_query_stmt, _query_params) = _query.query.get_compiler('config').as_sql()
        _query_sql = _query_stmt % _query_params

        _items = self._context.get_frame().items
        try:
            _query = (
                "SELECT i.*, rank FROM config_item i, ("
                "  SELECT id, SUM(rank) AS rank FROM ( " + str(_query_sql) + " ) AS rank GROUP BY rank.id"
                ") AS result WHERE result.id=i.id" )
            _where = ""
            _limit = ""
            if self._context.get_random_item():
                _rank_max = _items.raw(_query + _where + " ORDER BY result.rank DESC LIMIT 1")[0].rank
                _where = " AND result.rank < " + str(random.randint(0, _rank_max))
                _limit = " LIMIT 1"
            _items = _items.raw(_query + _where + " ORDER BY result.rank DESC" + _limit)
        except Exception as e:
            _items = _items.order_by('id').annotate(rank=Model.F('id'))
            _result['errors']['list'] = e

        _result['items'] = _items

        return _result

