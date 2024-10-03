import re
import random

from django.db import connections, models as Model
from django.db.models import functions as Function

from framarama.base import utils
from config.plugins import SortingPluginRegistry
from config.utils import context


class Context:

    def __init__(self, frame, random_item=False, sortings=None):
        self._frame = frame
        self._random_item = random_item
        self._sortings = sortings
        self._data = {'Item': self._frame.items.order_by(), 'Model': Model, 'Function': Function}
    
    def get_frame(self):
        return self._frame

    def get_random_item(self):
        return self._random_item

    def get_sortings(self):
        return self._sortings

    def get_data(self):
        return self._data


class Processor:

    def __init__(self, context):
        self._context = context
        self._instances = {}

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
        _sortings = self._context.get_sortings()
        if not _sortings:
            _sortings = self._context.get_frame().sortings.all()
        for _plugin, _sorting in SortingPluginRegistry.get_enabled(_sortings):
            _code = _plugin.run(_sorting, context.ResultValue(_sorting.get_config()), self._context)
            _code = re.sub(r"[\r\n]+\s*", "", _code)  # fix indent by removing newline/whitespaces
            try:
                _code = _code + ".annotate(pk=Model.F('pk'), rank=Model.F('rank')*Model.Value({}))".format(_sorting.weight)
                _code = _code + ".values('pk', 'rank')"
                _queries.append(utils.Process.eval(_code, _data))
            except Exception as e:
                _result['errors']['sorting{}'.format(_sorting.id)] = e

        # No query given, use the default ranking
        if len(_queries) == 0:
            _queries.append(_data['Item']
              .annotate(pk=Model.F('id'), rank=Model.Window(expression=Function.Rank(), order_by=Model.F('id').asc()))
              .values('pk', 'rank')
           )

        # Get raw SQL query using compiler as used in the Query code, but
        # this defaults to "default" connection and not "config" connection:
        # https://github.com/django/django/blob/6654289f5b350dfca3dc4f6abab777459b906756/django/db/models/sql/query.py#L293
        _conn_name = 'config' if 'config' in connections else 'default'

        # Surround queries with subquery to calculate rank differences
        _query_params = []
        for _i, _q in enumerate(_queries):
            (_sql, _sql_params) = _q.query.get_compiler(_conn_name).as_sql()
            _query_params.extend(_sql_params)
            _queries[_i] = "SELECT pk, (rank - COALESCE(LAG(rank) OVER(ORDER BY rank), 0)) AS rank_diff FROM ( " + str(_sql) + ") AS result_" + str(_i)
        _query = " UNION ALL ".join(_queries)

        _items = _data['Item']
        try:
            _query = (
                "SELECT i.*, (SUM(weight) OVER(ORDER BY weight, pk)) AS rank, weight FROM config_item i, ( SELECT pk, rank AS weight FROM ("
                "  SELECT pk AS pk, SUM(rank_diff) AS rank FROM (" + str(_query) + ") AS result_diff GROUP BY pk"
                ") AS result_sum) result WHERE result.pk=i.id"
            )
            if self._context.get_random_item():
                _rank_max = _items.raw(_query + " ORDER BY result.rank DESC LIMIT 1", _query_params)[0].rank
                _query = _query + " AND result.rank >= " + str(random.randint(0, _rank_max))
                _query = _query + " ORDER BY result.rank ASC LIMIT 1"
            else:
                _query = _query + " ORDER BY result.weight DESC, result.pk DESC"
            _items = _items.prefetch_related('source').raw(_query, _query_params)
            len(_items)
        except Exception as e:
            _items = _data['Item'].order_by('id').annotate(rank=Model.F('id'))
            _result['errors']['list'] = e

        _result['items'] = _items

        return _result

