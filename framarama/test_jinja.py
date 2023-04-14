import datetime
import zoneinfo

from unittest import TestCase

from framarama import jinja


class JinjaDateformatTestCase(TestCase):

    def test_dateformat(self):
        _now = datetime.datetime.now(tz=zoneinfo.ZoneInfo('UTC'))
        _result = jinja.date_format(_now)
        self.assertIsNotNone(_result)

    def test_dateformat(self):
        _now = datetime.datetime.now(tz=zoneinfo.ZoneInfo('UTC'))
        self.assertEqual("{:d}".format(_now.year), jinja.date_format(_now, '%Y'))
        self.assertEqual("{:02d}".format(_now.month), jinja.date_format(_now, '%m'))
        self.assertEqual("{:02d}".format(_now.day), jinja.date_format(_now, '%d'))
        self.assertEqual("{:02d}".format(_now.hour), jinja.date_format(_now, '%H'))
        self.assertEqual("{:02d}".format(_now.minute), jinja.date_format(_now, '%M'))
        self.assertEqual("{:02d}".format(_now.second), jinja.date_format(_now, '%S'))


class JinjaDurationTestCase(TestCase):

    def test_duration(self):
        _result = jinja.duration(datetime.timedelta(seconds=1))
        self.assertEqual('1 seconds', _result)
        _result = jinja.duration(datetime.timedelta(days=1))
        self.assertEqual('1 days', _result)
        _result = jinja.duration(datetime.timedelta(days=1, hours=2))
        self.assertEqual('1 days, 2 hours', _result)
        _result = jinja.duration(datetime.timedelta(days=1, hours=2, minutes=3))
        self.assertEqual('1 days, 2 hours, 3 minutes', _result)

    def test_duration_single_parts(self):
        _result = jinja.duration(datetime.timedelta(hours=2), ['days'])
        self.assertEqual('0 days', _result)
        _result = jinja.duration(datetime.timedelta(days=1), ['days'])
        self.assertEqual('1 days', _result)
        _result = jinja.duration(datetime.timedelta(days=1, hours=2), ['days'])
        self.assertEqual('1 days', _result)
        _result = jinja.duration(datetime.timedelta(days=1, hours=2, minutes=3), ['days'])
        self.assertEqual('1 days', _result)
        _result = jinja.duration(datetime.timedelta(days=1, hours=2, minutes=3), ['days'])
        self.assertEqual('1 days', _result)

    def test_duration_multiple_parts(self):
        _result = jinja.duration(datetime.timedelta(hours=2), ['days', 'hours'])
        self.assertEqual('2 hours', _result)
        _result = jinja.duration(datetime.timedelta(days=1), ['days', 'hours'])
        self.assertEqual('1 days', _result)
        _result = jinja.duration(datetime.timedelta(days=1, hours=2), ['days', 'hours'])
        self.assertEqual('1 days, 2 hours', _result)
        _result = jinja.duration(datetime.timedelta(days=1, hours=2, minutes=3), ['days', 'hours'])
        self.assertEqual('1 days, 2 hours', _result)
        _result = jinja.duration(datetime.timedelta(days=1, hours=2, minutes=3), ['days', 'hours'])
        self.assertEqual('1 days, 2 hours', _result)

    def test_duration_short(self):
        _result = jinja.duration(datetime.timedelta(hours=2), short=True)
        self.assertEqual('2 hours', _result)
        _result = jinja.duration(datetime.timedelta(days=2, hours=2), short=True)
        self.assertEqual('2 days', _result)

    def test_duration_short_parts(self):
        _result = jinja.duration(datetime.timedelta(hours=2), ['days'], short=True)
        self.assertEqual('0 days', _result)
        _result = jinja.duration(datetime.timedelta(days=2, hours=2), ['days'], short=True)
        self.assertEqual('2 days', _result)

    def test_duration_datetime(self):
        _result = jinja.duration(datetime.datetime.now(tz=zoneinfo.ZoneInfo('UTC')))
        self.assertEqual('0 seconds', _result)
        _result = jinja.duration(datetime.datetime.now(tz=zoneinfo.ZoneInfo('UTC'))-datetime.timedelta(hours=2))
        self.assertEqual('2 hours', _result)


class JinjaBase64TestCase(TestCase):

    def test_b64decode(self):
        _result = jinja.b64decode('SGVsbG8gd29ybGQ=')
        self.assertEqual(b'Hello world', _result)

    def test_b64encode(self):
        _result = jinja.b64encode(b'Hello world')
        self.assertEqual('SGVsbG8gd29ybGQ=', _result)


class JInjaGetattributeTestCase(TestCase):

    def test_getattribute_dict(self):
        self.assertEqual('value', jinja.get_attribute({'key':'value'}, 'key'))

    def test_getattribute_dict_level(self):
        self.assertEqual('value', jinja.get_attribute({'key':{'name':'value'}}, 'key.name'))

    def test_getattribute_obj(self):
        _now = datetime.datetime.now(tz=zoneinfo.ZoneInfo('UTC'))
        self.assertIsNotNone(jinja.get_attribute(_now, 'tzinfo'))

    def test_getattribute_obj_level(self):
        _now = datetime.datetime.now(tz=zoneinfo.ZoneInfo('UTC'))
        self.assertEqual('UTC', jinja.get_attribute(_now, 'tzinfo.key'))

    def test_getattribute_name(self):
        self.assertEqual('value', jinja.get_attribute({'key':'value'}, 'name:key'))

