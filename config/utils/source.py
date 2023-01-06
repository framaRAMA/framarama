import sys
import logging
import zoneinfo

from django.utils import timezone
from django.utils.dateparse import parse_datetime

from config.plugins import SourcePluginRegistry
from config.utils.data import DataType, DataContainer, NoopDataConverter
from config import models


logger = logging.getLogger(__name__)


class Context:

    def __init__(self, frame, source=None, data={}):
        self._frame = frame
        self._source = None
        self._data = data
    
    def get_frame(self):
        return self._frame

    def get_source(self):
        return self._source

    def get_input(self, name):
        if name not in self._data:
            return []
        return self._data[name]

    def set_output(self, name, data):
        self._data[name] = data


class Processor:

    def __init__(self, context):
        self._context = context
        self._instances = {}

    def get_plugin(self, plugin_name):
        return SourcePluginRegistry.get(plugin_name)

    def get_plugin_instance(self, plugin_name, instance_name):
        _instance_name = plugin_name + ':' + instance_name
        if _instance_name not in self._instances:
            self._instances[_instance_name] = self.get_plugin(plugin_name).impl()
        return self._instances[_instance_name]

    def get_model(self, step):
        return self.get_plugin(step.plugin).load_model(step.id)

    def process(self):
        _sources = self._context.get_frame().sources
        if self._context.get_source():
          _sources = _sources.filter(source=self._context.get_source())
        for _source in _sources.all():
            logger.info("Processing source {}".format(_source))
            _source.update_count = _source.update_count + 1
            _source.update_date_start = timezone.now()
            _source.save()

            try:
                _last_step = None
                for i, _step in enumerate(_source.steps.all()):
                    self._process_step(i+1, self.get_model(_step))
                    _last_step = _step
                if _last_step and _last_step.data_out:
                    _stats = self._process_items_updates(_source, _last_step)
                    _source.item_count_total = _stats['create'] + _stats['update']
                    _source.item_count_error = len(_stats['errors'])
                _source.update_date_end = timezone.now()
                _source.save()
            except Exception as e:
                _source.update_date_end = timezone.now()
                _source.update_error = getattr(e, 'message', repr(e))
                _source.save()
                raise e

    def _process_step(self, cnt, step):
        if step.data_in:
            _data_input = self._context.get_input(step.data_in)
        else:
            _data_input = [DataContainer(data=None, data_type=DataType(DataType.TYPE, 'string'), conv=NoopDataConverter())]
        
        if step.merge_in:
            if len(_data_input):
                _first = _data_input[0].copy()
                for _data in _data_input[1:]:
                    _first.append(_data)
                _data_input = [_first]
            else:
                _data_input = []
        
        _data_output = []
        for i, _data_in in enumerate(_data_input):
            _data_out = self._process_step_plugin(cnt, i+1, len(_data_input), step, _data_in)

            if step.loop_out and len(_data_out):
                _data_out = _data_out[0].items()

            logger.info("Result: {} items, {}".format(len(_data_out), _data_out))

            _data_output.extend(_data_out)
        if step.data_out:
            self._context.set_output(step.data_out, _data_output)

    def _process_step_plugin(self, cnt, i, icnt, step, _data_in):
        logger.info("Run step {}: {}/{} {}".format(cnt, i, icnt, step))
        if step.mime_in:
            _data_in = DataContainer(data=_data, data_type=DataType(DataType,MIME, step.mime_in))

        _plugin = self.get_plugin(step.plugin)
        _data_out = _plugin.run(step, _data_in, self._context, instance=step.instance)

        if not step.data_out:
            return []

        if step.mime_out:
            _data_out = [_data.convert(DataType(DataType.MIME, step.mime_out)) for _data in _data_out]

        return _data_out

    def _process_items_updates(self, source, last_step):
        _data_out = self._context.get_input(last_step.data_out)[0].convert(DataType(DataType.TYPE, 'dict'))
        _stats = self._process_items_update(source, _data_out)
        logger.info("Import completed: {} processed ({} created, {} updated, {} deleted, {} errors)".format(
            _stats['cnt'],
            _stats['create'],
            _stats['update'],
            _stats['delete'],
            len(_stats['errors'])))
        if len(_stats['errors']):
            logger.info("Last errors:\n- {}".format(
              "\n- ".join("{}: {}".format(e['item'], e['error']) for e in _stats['errors'])))
        return _stats

    def _process_items_update(self, source, data_out):
        _frame = self._context.get_frame()
        _existing = {_item.url: _item for _item in source.items.all()}
        _fields = self._item_mapping(source)
        _stats = {'cnt': 0, 'create': 0, 'update': 0, 'delete': 0, 'errors': []}

        logger.info("Collected {} items, {} existing items".format(
            len(data_out.get()),
            len(_existing)))

        for _data in data_out.get():
            if _stats['cnt'] % 100 == 0:
                logger.info("Processed {} items ({} created, {} updated, {} deleted, {} errors)".format(
                    _stats['cnt'],
                    _stats['create'],
                    _stats['update'],
                    _stats['delete'],
                    len(_stats['errors'])))
            _stats['cnt'] = _stats['cnt'] + 1
            _values = self._item_values(_fields, _data)

            _item_id = _values.get('id')
            _item_url = _values.get('url')
            _item_date_creation = _values.get('date_creation')

            try:
                if _item_id is None:
                    raise Exception("Item skipped, missing ID: {}".format(_values))

                if _item_url is None:
                    raise Exception("Item skipped, missing URL: {}".format(_values))

                if _item_date_creation is None:
                    raise Exception("Item skipped, missing creation date: {}".format(_values))

                if _item_url in _existing:
                    _item = _existing[_item_url]
                    _item.version = _item.version + 1
                    _stats_type = 'update'
                else:
                    _item = models.Item()
                    _item.frame = _frame
                    _item.source = source
                    _item.version = 0
                    _item.url = _item_url
                    _item.created = timezone.now()
                    _stats_type = 'create'

                _item.id_ext = _item_id
                _item.date_creation = _item_date_creation
                _item.updated = timezone.now()
                _item.save()

                if _stats_type == 'update':
                    _existing.pop(_item_url)
                _stats[_stats_type] = _stats[_stats_type] + 1
            except Exception as e:
                _stats['errors'].append({'item': _item_url, 'error': e})

        for _item in _existing.values():
            _item.delete()
            _stats['delete'] = _stats['delete'] + 1
            break

        return _stats

    def _item_mapping(self, source):
        _fields = {
            'id': 'int:' + source.map_item_id_ext,
            'url': 'str:' + source.map_item_url,
            'date_creation': 'date:' + source.map_item_date_creation
        }
        _map_item_meta = source.map_item_meta
        if _map_item_meta:
            _fields.update(dict(map(lambda l: l.split("="), _map_item_meta.splitlines())))
        return _fields

    def _item_values(self, fields, data):
        _values = {}
        for _field_target, _field_source in fields.items():
            if ':' in _field_source:
                (_field_type, _field_source) = _field_source.split(':')
            else:
                _field_type = 'str'
            if _field_source in data:
                _value = data.get(_field_source)
                if _field_type == 'str':
                    _value = str(_value)
                elif _field_type == 'int':
                    _value = int(_value)
                elif _field_type == 'date':
                    _value_parsed = parse_datetime(_value)
                    if _value_parsed and _value_parsed.tzinfo is None:
                        _value = _value_parsed.astimezone(zoneinfo.ZoneInfo('Europe/Berlin'))
                _values[_field_target] = _value
        return _values

