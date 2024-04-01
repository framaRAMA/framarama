import io
import sys
import csv
import json
import logging


logger = logging.getLogger(__name__)


class DataType:
    MIME = 'mime'
    TYPE = 'type'

    def __init__(self, handle_by, handle_type):
        self._handle_by = handle_by
        self._handle_type = handle_type

    def __repr__(self):
        return "{}:{}".format(self._handle_by, self._handle_type)

    def get_handle_by(self):
        return self._handle_by

    def get_handel_type(self):
        return self._handle_type


class DataConverter:

    def __init__(self):
        self._registry = {'input': {}, 'output': {}}

    def _register(self, direction, data_type, handler):
        self._registry[direction][str(data_type)] = handler

    def _supports(self, direction, data_type):
        return str(data_type) in self._registry[direction]

    def _convert(self, direction, data_type, data):
        _handler = self._registry[direction][str(data_type)]
        _data = _handler(data)
        return _data

    def register(self, direction, data_type, handler):
        self._register(direction, data_type, handler)

    def supports(self, direction, data_type):
        return self._supports(direction, data_type)

    def convert(self, direction, data_type, data):
        try:
            return self._convert(direction, data_type, data)
        except Exception as e:
            raise Exception("Error converting {} to {} with {}: {}".format(type(data), data_type, type(self).__name__, e)) from e
    
    def filter(self, data, filter_expr):
        return self._filter(data, filter_expr)


class NoopDataConverter(DataConverter):

    def __init__(self):
        DataConverter.__init__(self)


class JsonDataConverter(DataConverter):

    def __init__(self):
        DataConverter.__init__(self)
        self.register('input', DataType(DataType.MIME, 'application/json'), self._from_str)
        self.register('input', DataType(DataType.MIME, 'text/plain'), self._from_str)
        self.register('input', DataType(DataType.TYPE, 'string'), self._from_str)
        self.register('input', DataType(DataType.TYPE, 'dict'), self._from_dict)
        self.register('output', DataType(DataType.MIME, 'application/json'), self._to_str)
        self.register('output', DataType(DataType.TYPE, 'dict'), self._to_dict)
        self.register('output', DataType(DataType.TYPE, 'string'), self._to_str)

    def _from_str(self, string_data):
        return json.loads(string_data)

    def _from_dict(self, dict_data):
        return dict_data

    def _to_dict(self, json_data):
        return json_data
    
    def _to_str(self, json_data):
        return json.dumps(json_data)

    def _filter(self, json_data, filter_expr=None):
        if filter_expr is None:
            return json_data
        import jsonpath
        return jsonpath.JSONPath(filter_expr).parse(json_data)


class CsvDataConverter(DataConverter):

    def __init__(self):
        DataConverter.__init__(self)
        self.register('input', DataType(DataType.MIME, 'text/csv'), self._from_str)
        self.register('input', DataType(DataType.MIME, 'text/plain'), self._from_str)
        self.register('input', DataType(DataType.TYPE, 'string'), self._from_str)
        self.register('input', DataType(DataType.TYPE, 'dict'), self._from_dict)
        self.register('output', DataType(DataType.MIME, 'text/csv'), self._to_str)
        self.register('output', DataType(DataType.TYPE, 'dict'), self._to_dict)
        self.register('output', DataType(DataType.TYPE, 'string'), self._to_str)

    def _from_str(self, string_data):
        if type(string_data) == bytes:
            string_data = string_data.decode()
        _lines = [line for line in string_data.splitlines() if len(line)]
        _sample = "\n".join(_lines[:10])
        _sniffer = csv.Sniffer()
        _dialect = _sniffer.sniff(_sample)
        _headers = _sniffer.has_header(_sample)
        if _headers:
            _reader = csv.DictReader(_lines, dialect=_dialect)
        else:
            _reader = csv.reader(_lines, dialect=_dialect)
        _result = []
        for _row in _reader:
            _result.append(_row)
        return _result

    def _from_dict(self, dict_data):
        return dict_data

    def _to_dict(self, csv_data):
        return csv_data
    
    def _to_str(self, csv_data):
        _output = io.StringIO()
        _writer = csv.writer(_output, delimiter=";", quote=csv.QUOTE_MINIMAL)
        _writer.writerows(csv_data)
        return _output.getvalue()

    def _filter(self, json_data, filter_expr=None):
        raise Exception("Filtering not possbile in CSV data")


class DataContainer:
    CONVERTERS = [
        JsonDataConverter(),
        CsvDataConverter(),
    ]

    def __init__(self, data=None, data_type=None, conv=None):
        if conv is None:  # raw data is passed
            self._conv = self._converter('input', data_type=data_type)
            self._data = self._conv.convert('input', data=data, data_type=data_type)
        else:             # converted data is passed
            self._conv = conv
            self._data = data
        self._data_type = data_type

    def __repr__(self):
        return "<{} type={}, data={} size={}>".format(self.__class__.__name__, self._data_type, type(self._data).__name__, sys.getsizeof(self._data))

    def _converter(self, direction, data_type):
        for converter in DataContainer.CONVERTERS:
            if converter.supports(direction, data_type):
                return converter
        raise Exception("Can not find {} converter for {}".format(direction, data_type))

    def get(self):
        return self._data

    def get_type(self):
        return self._data_type

    def convert(self, data_type):
        if self._data is None or self._data_type is None:
            return None
    
        if self._conv.supports('input', data_type):
            return DataContainer(
                data=self._data,
                data_type=data_type,
                conv=self._conv)

        _conv = self._converter('input', data_type)
        return DataContainer(
            data=_conv.convert('input', data_type, self._data),
            data_type=data_type,
            conv=_conv)

    def filter(self, filter_expr):
        return DataContainer(
            data=self._conv.filter(self._data, filter_expr),
            data_type=self._data_type,
            conv=self._conv)

    def get_as_mime(self, mime_type):
        return self.convert(DataType(DataType.MIME, mime_type))

    def get_as_type(self, data_type):
        return self.convert(DataType(DataType.TYPE, data_type))

    def get_as_dict(self):
        return self.get_as_type('dict')

    def get_as_string(self):
        return self.get_as_type('string')

    def copy(self):
        return DataContainer(data=self._data, data_type=self._data_type, conv=self._conv)

    def items(self):
        _result = []
        for item in list(self._data):
            _result.append(DataContainer(item, data_type=self._data_type, conv=self._conv))
        return _result

    def append(self, data):
        if type(self._data) == str:
            self._data = self._data + data.get()
        elif type(self._data) == list:
            self._data.extend(data.get())
        elif type(self._data) == dict:
            self._data.update(data.get())
        else:
            return False
        return True

