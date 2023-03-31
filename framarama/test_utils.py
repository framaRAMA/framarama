import datetime

from unittest import TestCase

from framarama.base import utils


class JsonTestCase(TestCase):

    def test_from_dict(self):
        _data = utils.Json.from_dict({'a':'b', 'c':'d', 'd':[1, 2], 'e':{'f':'g', 'h':'i', 'j':[3, 4]}})
        self.assertEqual('{"a": "b", "c": "d", "d": [1, 2], "e": {"f": "g", "h": "i", "j": [3, 4]}}', _data)

    def test_from_dict(self):
        _data = utils.Json.to_dict('{"a": "b", "c": "d", "d": [1, 2], "e": {"f": "g", "h": "i", "j": [3, 4]}}')
        self.assertEqual({'a':'b', 'c':'d', 'd':[1, 2], 'e':{'f':'g', 'h':'i', 'j':[3, 4]}}, _data)

    def test_to_object_dict(self):
        _data = utils.Json.to_object_dict({'key':'value', 'nested':{'key':'value'}}, fields=['key', 'nested_key'])
        self.assertEqual({'key':'value', 'nested_key':'value'}, _data)

    def test_from_object_dict(self):
        _data = utils.Json.from_object_dict({'key':'value', 'nested_key':'value'})
        self.assertEqual({'key':'value', 'nested':{'key':'value'}}, _data)


class DateTimeTestCase(TestCase):

    def test_get(self):
        self.assertIsNotNone(utils.DateTime.get(datetime.datetime.now()))

    def test_get_sub(self):
        _now = utils.DateTime.get(datetime.datetime.now())
        _past = utils.DateTime.get(datetime.datetime.now(), sub='01:00:00')
        self.assertTrue(_past < _now, 'Past date is not in past')

    def test_get_add(self):
        _now = utils.DateTime.get(datetime.datetime.now())
        _future = utils.DateTime.get(datetime.datetime.now(), add='01:00:00')
        self.assertTrue(_future > _now, 'Future date is not in future')

    def test_now(self):
        self.assertIsNotNone(utils.DateTime.now())

    def test_now_tz(self):
        _now = utils.DateTime.now(tz='UTC')
        self.assertEqual('UTC', _now.tzinfo.key)
        _now = utils.DateTime.now(tz='Europe/Berlin')
        self.assertEqual('Europe/Berlin', _now.tzinfo.key)

    def test_now_sub(self):
        _now = utils.DateTime.now()
        _past = utils.DateTime.now(sub='01:00:00')
        self.assertTrue(_past < _now, 'Past date is not in past')

    def test_now_add(self):
        _now = utils.DateTime.now()
        _future = utils.DateTime.now(add='01:00:00')
        self.assertTrue(_future > _now, 'Future date is not in future')

    def test_midnight(self):
        _midnight = utils.DateTime.midnight()
        self.assertEqual(0, _midnight.hour, 'Midnight does not have hour 0')
        self.assertEqual(0, _midnight.minute, 'Midnight does not have minute 0')
        self.assertEqual(0, _midnight.second, 'Midnight does not have second 0')
        self.assertEqual(0, _midnight.microsecond, 'Midnight does not have microsecond 0')

    def test_midnight_tz(self):
        _midnight = utils.DateTime.midnight(tz='Europe/Berlin')
        self.assertEqual(0, _midnight.hour, 'Midnight does not have hour 0')
        self.assertEqual(0, _midnight.minute, 'Midnight does not have minute 0')
        self.assertEqual(0, _midnight.second, 'Midnight does not have second 0')
        self.assertEqual(0, _midnight.microsecond, 'Midnight does not have microsecond 0')

    def test_delta(self):
        _delta = utils.DateTime.delta('08:12:59')
        self.assertIsInstance(_delta, datetime.timedelta, 'Delta is not a timedelta object')
        self.assertEqual(0, _delta.days, 'Delta have not 0 days')
        self.assertEqual((8*60+12)*60+59, _delta.seconds, 'Delta have no {} seconds'.format((8*60+12)*60+59))

    def test_delta_time(self):
        _ten = utils.DateTime.delta('00:10:00')
        _delta = utils.DateTime.delta(_ten)
        self.assertEqual(_ten, _delta)

    def test_delta_int(self):
        _delta = utils.DateTime.delta(300)
        self.assertEqual(300, _delta.seconds)

    def test_delta_float(self):
        _delta = utils.DateTime.delta(300.0)
        self.assertEqual(300, _delta.seconds)

    def test_delta_dict(self):
        _delta = utils.DateTime.delta_dict('08:12:59')
        self.assertIsInstance(_delta, dict, 'Delta is not a dict object')
        self.assertEqual(0, _delta['days'], 'Delta have not 0 days')
        self.assertEqual(8, _delta['hours'], 'Delta have not 8 hours')
        self.assertEqual(12, _delta['minutes'], 'Delta have not 12 minutes')
        self.assertEqual(59, _delta['seconds'], 'Delta have not 59 seconds')
        self.assertEqual((8*60+12)*60+59, _delta['total'], 'Delta have no {} seconds'.format((8*60+12)*60+59))

    def test_reached(self):
        _time = utils.DateTime.now()
        self.assertTrue(utils.DateTime.reached(_time, utils.DateTime.delta(minutes=-10)))
        self.assertFalse(utils.DateTime.reached(_time, utils.DateTime.delta(minutes=10)))

    def test_in_range_list(self):
        _range = [utils.DateTime.delta(minutes=-10), utils.DateTime.delta(minutes=10)]
        _result = utils.DateTime.in_range(utils.DateTime.now(), _range)
        self.assertEqual(_range[0], _result)
        _range = [utils.DateTime.delta(minutes=-10), utils.DateTime.delta(minutes=-5)]
        _result = utils.DateTime.in_range(utils.DateTime.now(), _range)
        self.assertEqual(_range[1], _result)
        _range = [utils.DateTime.delta(minutes=5), utils.DateTime.delta(minutes=10)]
        _result = utils.DateTime.in_range(utils.DateTime.now(sub='00:20:00'), _range)
        self.assertEqual(_range[1], _result)
        _range = [utils.DateTime.delta(minutes=10), utils.DateTime.delta(minutes=10)]
        _result = utils.DateTime.in_range(utils.DateTime.now(sub='00:20:00'), _range)
        self.assertEqual(_range[1], _result)

    def test_in_range_dict(self):
        _range = {'first': utils.DateTime.delta(minutes=-10), 'second': utils.DateTime.delta(minutes=10)}
        _result = utils.DateTime.in_range(utils.DateTime.now(), _range)
        self.assertEqual('first', _result)
        _range = {'first': utils.DateTime.delta(minutes=-10), 'second': utils.DateTime.delta(minutes=-5)}
        _result = utils.DateTime.in_range(utils.DateTime.now(), _range)
        self.assertEqual('second', _result)
        _range = {'first': utils.DateTime.delta(minutes=5), 'second': utils.DateTime.delta(minutes=10)}
        _result = utils.DateTime.in_range(utils.DateTime.now(sub='00:20:00'), _range)
        self.assertEqual('second', _result)
        _range = {'first': utils.DateTime.delta(minutes=10), 'second': utils.DateTime.delta(minutes=10)}
        _result = utils.DateTime.in_range(utils.DateTime.now(sub='00:20:00'), _range)
        self.assertEqual('second', _result)

    def test_utc(self):
        _time = utils.DateTime.now()
        _time_utc = _time - datetime.timedelta(seconds=_time.utcoffset().total_seconds())
        _utc = utils.DateTime.utc(_time)
        self.assertEqual(_time_utc.replace(tzinfo=None).isoformat() + 'Z', _utc)

    def test_parse(self):
        _time = utils.DateTime.parse('2023-01-01T15:45:10')
        self.assertEqual(2023, _time.year)
        self.assertEqual(1, _time.month)
        self.assertEqual(1, _time.day)
        self.assertEqual(15, _time.hour)
        self.assertEqual(45, _time.minute)
        self.assertEqual(10, _time.second)

    def test_zoned(self):
        with utils.DateTime.zoned('UTC'):
            _time_utc = utils.DateTime.now()
        with utils.DateTime.zoned('Europe/Berlin'):
            _time_europe = utils.DateTime.now()
        self.assertNotEqual(_time_utc.tzinfo.key, _time_europe.tzinfo.key)


class ClassesTestCase(TestCase):

    def test_load_python_module(self):
        _datetime = utils.Classes.load("datetime")
        self.assertIsNotNone(_datetime, 'Python module datetime not loaded')
        import datetime
        self.assertEqual(_datetime, datetime, 'Module is not datetime')

    def test_load_python_module_wrong(self):
        with self.assertRaises(ModuleNotFoundError):
            utils.Classes.load("wrong")

    def test_load_python_module_fallback(self):
        _datetime = utils.Classes.load("datetimeX", fallback="datetime")
        self.assertIsNotNone(_datetime, 'Python module datetime not loaded')
        import datetime
        self.assertEqual(_datetime, datetime, 'Python module is not datetime')

    def test_load_fqcn(self):
        _case = utils.Classes.load("framarama.test_utils.ClassesTestCase", fqcn=True)
        self.assertIsNotNone(_case, 'Class is not loaded')
        self.assertEqual(_case, ClassesTestCase, 'Class is not a ClassesTestCase')

    def test_load_fqcn_wrong(self):
        with self.assertRaises(ModuleNotFoundError):
            utils.Classes.load("framarama.test_utils.Wrong", fqcn=True)

    def test_load_fqcn_fallback(self):
        _datetime = utils.Classes.load("framarama.test_utils.Wrong", fqcn=True, fallback="datetime.datetime")
        self.assertIsNotNone(_datetime, 'Class is not loaded')
        import datetime
        self.assertEqual(_datetime, datetime.datetime, 'Class is not a datetime')


