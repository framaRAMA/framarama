import sys
import logging
import zoneinfo

from django.utils import timezone
from django.utils.dateparse import parse_datetime

from config.plugins import SourcePluginRegistry
from config.utils.data import DataType, DataContainer, NoopDataConverter
from config import models


logger = logging.getLogger(__name__)


class FrameContextData:

    def __init__(self):
        self._data = None

    def get_data(self):
        return self._data

    def set_data(self, data):
        self._data = data


class FrameContext:

    def __init__(self, frame):
        self._frame = frame
        self._data = {}
    
    def get_frame(self):
        return self._frame

    def get_input(self, name):
        if name not in self._data:
            return []
        return self._data[name]

    def set_output(self, name, data):
        self._data[name] = data


class FrameProcessor:

    def __init__(self, frame):
        self._frame = frame
        self._plugins = {}

    def get_plugin(self, plugin_name, instance_name):
        _plugin_instance_name = plugin_name + ':' + instance_name
        if _plugin_instance_name not in self._plugins:
            _plugin = SourcePluginRegistry.get(plugin_name)
            self._plugins[_plugin_instance_name] = _plugin.Implementation()
        return self._plugins[_plugin_instance_name]

    def update(self):
        logger.info("Updating frame {}".format(self._frame))
        _ctx = FrameContext(self._frame)
        for _source in self._frame.sources.all():
           self._update_source(self._frame, _source, _ctx)

    def _update_source(self, frame, source, ctx):
        _last = None
        logger.info("Processing source {}".format(source))
        source.update_count = source.update_count + 1
        source.update_date_start = timezone.now()
        source.save()
        try:
            for i, _step in enumerate(source.steps.all()):
                self._update_source_step(i+1, _step, ctx)
                _last = _step
            if _last and _last.data_out:
                _data_out = ctx.get_input(_last.data_out)[0].convert(DataType(DataType.TYPE, 'dict'))
                _stats = self._update_source_items(frame, source, _data_out)
                logger.info("Import completed: {} processed, {} created, {} updated, {} deleted, {} errors)".format(
                    _stats['cnt'],
                    _stats['create'],
                    _stats['update'],
                    _stats['delete'],
                    len(_stats['errors'])))
                if len(_stats['errors']):
                    logger.info("Last errors:\n- {}".format(
                      "\n- ".join("{}: {}".format(e['item'], e['error']) for e in _stats['errors'])))
                source.item_count_total = _stats['create'] + _stats['update']
                source.item_count_error = len(_stats['errors'])
            source.update_date_end = timezone.now()
            source.save()
        except Exception as e:
            source.update_date_end = timezone.now()
            source.update_error = getattr(e, 'message', repr(e))
            source.save()
            raise

    def _update_source_items(self, frame, source, data_out):
        _exists = {_item.url: _item for _item in source.items.all()}
        _fields = {
            'id': 'int:' + source.map_item_id_ext,
            'url': 'str:' + source.map_item_url,
            'date_creation': 'date:' + source.map_item_date_creation
        }
        if source.map_item_meta:
            _fields.update(dict(map(lambda l: l.split("="), source.map_item_meta.splitlines())))
        _stats = {'cnt': 0, 'create': 0, 'update': 0, 'delete': 0, 'errors': []}
        logger.info("Collected {} items, {} existing items".format(len(data_out.get()), len(_exists)))
        for _data in data_out.get():
            if _stats['cnt'] % 100 == 0:
                logger.info("Processed {} items ({} created, {} updated, {} deleted, {} errors)".format(
                    _stats['cnt'],
                    _stats['create'],
                    _stats['update'],
                    _stats['delete'],
                    len(_stats['errors'])))
            _stats['cnt'] = _stats['cnt'] + 1
            _values = {}
            for _field_target, _field_source in _fields.items():
                if ':' in _field_source:
                    (_field_type, _field_source) = _field_source.split(':')
                else:
                    _field_type = 'str'
                if _field_source in _data:
                    _value = _data.get(_field_source)
                    if _field_type == 'str':
                        _value = str(_value)
                    elif _field_type == 'int':
                        _value = int(_value)
                    elif _field_type == 'date':
                        _value_parsed = parse_datetime(_value)
                        if _value_parsed and _value_parsed.tzinfo is None:
                            _value = _value_parsed.astimezone(zoneinfo.ZoneInfo('Europe/Berlin'))
                    _values[_field_target] = _value

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

                if _item_url in _exists:
                    _item = _exists[_item_url]
                    _stats_type = 'update'
                else:
                    _item = models.Item()
                    _item.frame = frame
                    _item.source = source
                    _item.url = _item_url
                    _item.created = timezone.now()
                    _stats_type = 'create'

                _item.id = _item_id
                _item.date_creation = _item_date_creation
                _item.updated = timezone.now()
                _item.save()

                if _stats_type == 'update':
                    _exists.pop(_item_url)
                _stats[_stats_type] = _stats[_stats_type] + 1
            except Exception as e:
                _stats['errors'].append({'item': _item_url, 'error': e})
        logger.info(_exists)
        for _item in _exists.values():
            _item.delete()
            _stats['delete'] = _stats['delete'] + 1
            break
        return _stats

    def _update_source_step(self, cnt, step, ctx):
        _plugin = self.get_plugin(step.plugin, step.instance)
        _step = _plugin.Model.objects.filter(pk=step.id).get()
        if _step.data_in:
            _data_input = ctx.get_input(_step.data_in)
        else:
            _data_input = [DataContainer(data=None, data_type=DataType(DataType.TYPE, 'string'), conv=NoopDataConverter())]
        
        if _step.merge_in:
            if len(_data_input):
                _first = _data_input[0].copy()
                for _data in _data_input[1:]:
                    _first.append(_data)
                _data_input = [_first]
            else:
                _data_input = []
        
        _data_output = []
        for i, _data_in in enumerate(_data_input):
            _data_out = self._update_source_step_run(cnt, i+1, len(_data_input), ctx, _plugin, _step, _data_in)

            if _step.loop_out and len(_data_out):
                _data_out = _data_out[0].items()

            logger.info("Result: {} items, {}".format(len(_data_out), _data_out))

            _data_output.extend(_data_out)
        if _step.data_out:
          ctx.set_output(_step.data_out, _data_output)

    def _update_source_step_run(self, cnt, i, icnt, ctx, _plugin, _step, _data_in):
        logger.info("Run step {}: {}/{} {}".format(cnt, i, icnt, _step))
        if _step.mime_in:
            _data_in = DataContainer(data=_data, data_type=DataType(DataType,MIME, _step.mime_in))

        _data_out = _plugin.run(_step, _data_in, ctx)

        if not _step.data_out:
            return []

        if _step.mime_out:
            _data_out = [_data.convert(DataType(DataType.MIME, _step.mime_out)) for _data in _data_out]

        return _data_out


class FrameSourceProcessor:
    pass

