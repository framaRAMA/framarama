import os
import datetime
import zoneinfo

from unittest import TestCase

from django.utils import timezone

from framarama.base import utils


class FilesystemTestCase(TestCase):

    def test_file_wrte(self):
        utils.Filesystem.file_write('test', b'Hello World!');
        self.assertTrue(os.path.exists('test'))
        os.remove('test')

    def test_file_read(self):
        with open('test', 'wb') as f:
            f.write(b'Hello World!')
            f.close()
        _result = utils.Filesystem.file_read('test');
        os.remove('test')
        self.assertEquals(b'Hello World!', _result)

    def test_file_copy(self):
        with open('test1', 'wb') as f:
            f.write(b'Hello World!')
            f.close()
        utils.Filesystem.file_copy('test1', 'test2')
        _exists1 = os.path.exists('test1')
        _exists2 = os.path.exists('test2');
        os.remove('test1')
        os.remove('test2')
        self.assertTrue(_exists1)
        self.assertTrue(_exists2)

    def test_file_delete(self):
        with open('test', 'wb') as f:
            f.write(b'Hello World!')
            f.close()
        utils.Filesystem.file_delete('test')
        _exists = os.path.exists('test')
        if _exists:
            os.remove('test')
        self.assertFalse(_exists)

    def test_file_match(self):
        open('test-1', 'w').close()
        open('test-2', 'w').close()
        open('test-3', 'w').close()
        open('test-4', 'w').close()
        _result_files_all = utils.Filesystem.file_match('.', 'test-(.*)')
        _result_files_restricted = utils.Filesystem.file_match('.', 'test-([12])')
        os.remove('test-1')
        os.remove('test-2')
        os.remove('test-3')
        os.remove('test-4')
        self.assertEqual([('test-1', '1'), ('test-2', '2'), ('test-3', '3'), ('test-4', '4')], _result_files_all)
        self.assertEqual([('test-1', '1'), ('test-2', '2')], _result_files_restricted)

    def test_file_exists(self):
        with open('test', 'wb') as f:
            f.write(b'Hello World!')
            f.close()
        _exists = utils.Filesystem.file_exists('test')
        os.remove('test')
        self.assertTrue(_exists)

    def test_file_size(self):
        with open('test', 'wb') as f:
            f.write(b'Hello World!')
            f.close()
        _size = utils.Filesystem.file_size('test')
        os.remove('test')
        self.assertEquals(12, _size)

    def test_file_rotate(self):
        open('test-1.txt', 'w').close()
        open('test-2.txt', 'w').close()
        open('test-3.txt', 'w').close()
        open('test-4.txt', 'w').close()
        _result = utils.Filesystem.file_rotate('./', 'test-(.*)\.(.*)', 'test-{}.{}', 3, ['txt'])
        os.remove('test-2.txt')
        os.remove('test-3.txt')

    def test_file_rotate_start(self):
        open('test-1.txt', 'w').close()
        open('test-2.txt', 'w').close()
        open('test-3.txt', 'w').close()
        open('test-4.txt', 'w').close()
        _result = utils.Filesystem.file_rotate('./', 'test-(.*)\.(.*)', 'test-{}.{}', 3, ['txt'], start=1)
        os.remove('test-1.txt')
        os.remove('test-3.txt')

    def test_file_rotate_start_rev(self):
        open('test-1.txt', 'w').close()
        open('test-2.txt', 'w').close()
        open('test-3.txt', 'w').close()
        open('test-4.txt', 'w').close()
        _result = utils.Filesystem.file_rotate('./', 'test-(.*)\.(.*)', 'test-{}.{}', 3, ['txt'], start=1, reverse=True)
        os.remove('test-1.txt')
        os.remove('test-2.txt')


class ProcessTestCase(TestCase):

    def test_exec_run(self):
        _result = utils.Process.exec_run('ls')
        self.assertIsNotNone('', _result)

    def test_exec_run_args(self):
        _result = utils.Process.exec_run(['ls', '-l'])
        self.assertIsNotNone('', _result)

    def test_exec_run_error(self):
        with self.assertRaises(FileNotFoundError):
            _result = utils.Process.exec_run(['notfound'])

    def test_exec_run_bytes_arg(self):
        _user = utils.Process.exec_run(['whoami'])
        _result = utils.Process.exec_run(['id', _user.strip()])
        self.assertIsNotNone(_result)

    def test_exec_run_env(self):
        _result = utils.Process.exec_run(['bash', '-c', 'echo -n ,$VAR1,$VAR2,'], env={'VAR1':'Hello'})
        self.assertEqual(b',Hello,,', _result)

    def test_exec_bg(self):
        _result = utils.Process.exec_bg('ls')
        self.assertIsNotNone(_result)

    def test_exec_search(self):
        _result = utils.Process.exec_search('ls')
        self.assertIsNotNone(_result)

    def test_exec_running(self):
        _result = utils.Process.exec_search('python')
        self.assertIsNotNone(_result)

    def test_eval(self):
        _result = utils.Process.eval('42')
        self.assertEqual(42, _result)


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

    def test_tz(self):
        _tz = utils.DateTime.tz()
        self.assertEqual(timezone.get_current_timezone(), _tz)

    def test_tz_as_string(self):
        _tz = utils.DateTime.tz('Europe/Berlin')
        self.assertEqual('Europe/Berlin', _tz.key)

    def test_tz_as_zoneinfo(self):
        _tz = utils.DateTime.tz(zoneinfo.ZoneInfo('Europe/Berlin'))
        self.assertEqual('Europe/Berlin', _tz.key)

    def test_as_tz(self):
        _time = utils.DateTime.now(tz='UTC')
        _time_tz = utils.DateTime.as_tz(_time, 'Europe/Berlin')
        self.assertNotEqual(_time.tzinfo, _time_tz.tzinfo)
        self.assertEqual(_time.day, _time_tz.day)
        self.assertEqual(_time.month, _time_tz.month)
        self.assertEqual(_time.year, _time_tz.year)
        self.assertEqual(_time.hour, _time_tz.hour)
        self.assertEqual(_time.minute, _time_tz.minute)
        self.assertEqual(_time.second, _time_tz.second)

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

    def test_utc_none(self):
        _utc = utils.DateTime.utc(None)
        self.assertIsNone(_utc)

    def test_utc(self):
        _time = utils.DateTime.now()
        _time_utc = _time - datetime.timedelta(seconds=_time.utcoffset().total_seconds())
        _utc = utils.DateTime.utc(_time)
        self.assertEqual(_time_utc.replace(tzinfo=None).isoformat() + 'Z', _utc)

    def test_utc_timestamp(self):
        _time = utils.DateTime.now()
        _time_utc = _time - datetime.timedelta(seconds=_time.utcoffset().total_seconds())
        _utc = utils.DateTime.utc(_time, True)
        self.assertEqual(_time_utc.replace(tzinfo=None).timestamp(), _utc)

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


class ExceptionsTestCase(TestCase):

    def test_traceback(self):
        try:
            raise Exception("Raise test exception to verify")
        except Exception as e:
            _msg = utils.Exceptions.traceback()
        self.assertIsNotNone(_msg)
        self.assertIn('Raise test exception to verify', _msg)
        self.assertIn('Traceback', _msg)


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

    def test_subclasses(self):
        _classes = utils.Classes.subclasses(utils.Classes)
        self.assertEqual([utils.Classes], _classes)

    def test_subclasses_multi(self):
        class Parent:
            pass
        class Child1(Parent):
            pass
        class Child2(Parent):
            pass
        class SubChild1(Child1):
            pass
        _classes = utils.Classes.subclasses(Parent)
        self.assertEqual(4, len(_classes))
        self.assertTrue(Parent in _classes)
        self.assertTrue(Child1 in _classes)
        self.assertTrue(Child2 in _classes)
        self.assertTrue(SubChild1 in _classes)
        _classes_root = utils.Classes.subclasses(Parent, False)
        self.assertEqual(3, len(_classes_root))
        self.assertTrue(Child1 in _classes_root)
        self.assertTrue(Child2 in _classes_root)
        self.assertTrue(SubChild1 in _classes_root)


class ListTestCase(TestCase):

    def test_chunked_list(self):
        _data = [('k' + str(_i), 'v' + str(_i)) for _i in range(1, 51)]
        for _result in utils.Lists.chunked(_data, 1):
            self.assertEqual(1, len(_result))
        for _result in utils.Lists.chunked(_data, 10):
            self.assertEqual(10, len(_result))

    def test_chunked_generator(self):
        _data = (('k' + str(_i), 'v' + str(_i)) for _i in range(1, 51))
        for _result in utils.Lists.chunked(_data, 1):
            self.assertEqual(1, len(_result))
        for _result in utils.Lists.chunked(_data, 10):
            self.assertEqual(10, len(_result))

    def test_process(self):
        for sstart, send, tstart, tend, ccnt, ucnt, dcnt in [
            (1, 51,  1, 51,  0, 50,  0),
            (1, 51,  1, 41, 10, 40,  0),
            (1, 41,  1, 51,  0, 40, 10),
            (1, 51, 41, 71, 40, 10, 20),
        ]:
            create = []
            update = []
            delete = []
            _sdata = [('k' + str(_i), 'v' + str(_i)) for _i in range(sstart, send)]
            _sids = [_id for _id, _val in _sdata]
            _tdata = [('k' + str(_i), 'v' + str(_i)) for _i in range(tstart, tend)]
            _tids = [_id for _id, _val in _tdata]
            with self.subTest("sstart={}, send={}, tstart={}, send={}".format(sstart, send, tstart, tend)):
                _stats = utils.Lists.process(
                    source=_sdata,
                    target_match=lambda ids: [(_i, 'v' + str(_i)) for _i in ids if _i in _tids],
                    target=_tdata,
                    source_match=lambda ids: [(_i, 'v' + str(_i)) for _i in ids if _i in _sids],
                    size=10,
                    create_func=lambda id, val: create.append(val),
                    update_func=lambda id, sval, tval: update.append(sval),
                    delete_func=lambda id, val: delete.append(val))
                self.assertEqual(ccnt, len(create))
                self.assertEqual(ucnt, len(update))
                self.assertEqual(dcnt, len(delete))
                self.assertEqual(ccnt+ucnt+dcnt, _stats['total'])
                self.assertEqual(ccnt, _stats['create'])
                self.assertEqual(ucnt, _stats['update'])
                self.assertEqual(dcnt, _stats['delete'])

    def test_from_tree(self):
        _items = [
          {'id': 1, 'name': 'Item 1', 'children': [{'id': 11, 'name': 'Item 1.1'}, {'id': 12, 'name': 'Item 1.2'}]},
          {'id': 2, 'name': 'Item 2', 'children': [{'id': 21, 'name': 'Item 2.1'}, {'id': 22, 'name': 'Item 2.2'}]}
        ]
        _result = utils.Lists.from_tree(_items, child_name='children', parent_name='parent')
        self.assertEquals(6, len(_result))
        self.assertEquals('Item 1', _result['0']['name'])
        self.assertIsNone(_result['0']['parent'])
        self.assertEquals('Item 1.1', _result['0.0']['name'])
        self.assertEquals('0', _result['0.0']['parent'])
        self.assertEquals('Item 1.2', _result['0.1']['name'])
        self.assertEquals('0', _result['0.1']['parent'])
        self.assertEquals('Item 2', _result['1']['name'])
        self.assertIsNone(_result['1']['parent'])
        self.assertEquals('Item 2.1', _result['1.0']['name'])
        self.assertEquals('1', _result['1.0']['parent'])
        self.assertEquals('Item 2.2', _result['1.1']['name'])
        self.assertEquals('1', _result['1.1']['parent'])

    def test_from_tree_idname(self):
        _items = [
          {'id': 1, 'name': 'Item 1', 'children': [{'id': 11, 'name': 'Item 1.1'}, {'id': 12, 'name': 'Item 1.2'}]},
          {'id': 2, 'name': 'Item 2', 'children': [{'id': 21, 'name': 'Item 2.1'}, {'id': 22, 'name': 'Item 2.2'}]}
        ]
        _result = utils.Lists.from_tree(_items, 'children', 'parent', 'id')
        self.assertEquals(6, len(_result))
        self.assertEquals('Item 1', _result[1]['name'])
        self.assertIsNone(_result[1]['parent'])
        self.assertEquals('Item 1.1', _result[11]['name'])
        self.assertEquals(1, _result[11]['parent'])
        self.assertEquals('Item 1.2', _result[12]['name'])
        self.assertEquals(1, _result[12]['parent'])
        self.assertEquals('Item 2', _result[2]['name'])
        self.assertIsNone(_result[2]['parent'])
        self.assertEquals('Item 2.1', _result[21]['name'])
        self.assertEquals(2, _result[21]['parent'])
        self.assertEquals('Item 2.2', _result[22]['name'])
        self.assertEquals(2, _result[22]['parent'])

    def test_from_tree_nochild(self):
        _items = [
          {'id': 1, 'name': 'Item 1'},
          {'id': 2, 'name': 'Item 2'}
        ]
        _result = utils.Lists.from_tree(_items, child_name='children', parent_name='parent')
        self.assertEquals(2, len(_result))
        self.assertEquals('Item 1', _result['0']['name'])
        self.assertIsNone(_result['0']['parent'])
        self.assertEquals('Item 2', _result['1']['name'])
        self.assertIsNone(_result['1']['parent'])


    def test_to_tree(self):
        _items = {
          '0': {'id': 1, 'name': 'Item 1'},
          '0.1': {'id': 11, 'name': 'Item 11'},
          '0.2': {'id': 12, 'name': 'Item 12'},
          '1': {'id': 2, 'name': 'Item 2'},
          '1.1': {'id': 21, 'name': 'Item 21'},
          '1.2': {'id': 22, 'name': 'Item 22'},
        }
        _result = utils.Lists.to_tree(_items, child_name='children', parent_name='parent')
        self.assertEquals(2, len(_result))
        self.assertEquals(1, _result[0]['id'])
        self.assertIsNone(_result[0]['parent'])
        self.assertEquals(11, _result[0]['children'][0]['id'])
        self.assertEquals(1, _result[0]['children'][0]['parent']['id'])
        self.assertEquals(12, _result[0]['children'][1]['id'])
        self.assertEquals(1, _result[0]['children'][1]['parent']['id'])
        self.assertEquals(2, _result[1]['id'])
        self.assertIsNone(_result[1]['parent'])
        self.assertEquals(21, _result[1]['children'][0]['id'])
        self.assertEquals(2, _result[1]['children'][0]['parent']['id'])
        self.assertEquals(22, _result[1]['children'][1]['id'])
        self.assertEquals(2, _result[1]['children'][1]['parent']['id'])

    def test_from_annotated(self):
        _items = [
          ({'id': 1, 'name': 'Item 1'}, {'open': True, 'close':[]}),
          ({'id': 11, 'name': 'Item 11'}, {'open': True, 'close':[]}),
          ({'id': 12, 'name': 'Item 12'}, {'open': False, 'close':[0]}),
          ({'id': 2, 'name': 'Item 2'}, {'open': False, 'close':[]}),
          ({'id': 21, 'name': 'Item 21'}, {'open': True, 'close':[]}),
          ({'id': 22, 'name': 'Item 22'}, {'open': False, 'close':[0]}),
        ]
        _result = utils.Lists.from_annotated(_items)
        self.assertEquals(6, len(_result))
        self.assertEquals(1, _result['0']['id'])
        self.assertEquals(11, _result['0.0']['id'])
        self.assertEquals(12, _result['0.1']['id'])
        self.assertEquals(2, _result['1']['id'])
        self.assertEquals(21, _result['1.0']['id'])
        self.assertEquals(22, _result['1.1']['id'])

    def test_map_tree(self):
        _items = [
          {'id': 1, 'name': 'Item 1', 'children': [{'id': 11, 'name': 'Item 1.1'}, {'id': 12, 'name': 'Item 1.2'}]},
          {'id': 2, 'name': 'Item 2', 'children': [{'id': 21, 'name': 'Item 2.1'}, {'id': 22, 'name': 'Item 2.2'}]}
        ]
        _result = utils.Lists.map_tree(_items, lambda item:{'id': item['id']}, child_name='children')
        self.assertEquals(2, len(_result))
        self.assertEquals(1, _result[0]['id'])
        self.assertEquals(11, _result[0]['children'][0]['id'])
        self.assertEquals(12, _result[0]['children'][1]['id'])
        self.assertEquals(2, _result[1]['id'])
        self.assertEquals(21, _result[1]['children'][0]['id'])
        self.assertEquals(22, _result[1]['children'][1]['id'])


class TemplateTestCase(TestCase):

    def test_evaluate_none(self):
        self.assertIsNone(utils.Template.render(None))

    def test_evaluate_no_resolver(self):
        self.assertEqual('hello world', utils.Template.render("hello world"))

    def test_evaluate_no_resolver_key_missing(self):
        self.assertEqual('', utils.Template.render("{{missing}}"))

    def test_evaluate_keys(self):
        self.assertEqual('value', utils.Template.render("{{test['test']}}", {
            'test': 'value'
        }))

    def test_evaluate_quotes(self):
        self.assertEqual('"some quotes"', utils.Template.render('"some quotes"'))
        self.assertEqual("'some quotes'", utils.Template.render("'some quotes'"))

    def test_evaluate_slice(self):
        self.assertEqual('2468', utils.Template.render('{{(test)[1:8:2]|join}}', {
            'test': [1,2,3,4, 5, 6, 7, 8, 9, 10]
        }))

    def test_evaluate_split(self):
        self.assertEqual('this', utils.Template.render('{{test|split|first}}', {
            'test': 'this is a test'
        }))

    def test_valuate_keys(self):
        self.assertEqual('aceh', utils.Template.render('{{test|keys|join}}', {
            'test', {'a':'b', 'c':'d', 'e':'f', 'h':'i'}
        }))

    def test_evaluate_long(self):
        _text = """
hello world
"""
        self.assertEqual("\nhello world\n", utils.Template.render(_text))

    def test_evaluate_long_quotes(self):
        _text = """
hello \"\"\" world \"\"\"
"""
        self.assertEqual('\nhello """ world """\n', utils.Template.render(_text))

    def test_evaluate_long_html(self):
        _context = context.Context()
        _text = """
<html>
<body>
  <a href="http://github.com/framarama/">framaRAMA</a>
</body>
</html>
"""
        self.assertEqual('\n<html>\n<body>\n  <a href="http://github.com/framarama/">framaRAMA</a>\n</body>\n</html>\n', utils.Template.render(_text))

    def test_evaluate_long_script(self):
        _context = context.Context()
        _text = """
<html>
<head>
  <script>
  function dummy() {
    return 'hello world';
  }
  </script>
</head>
<body/>
</html>
"""
        self.assertEqual('\n<html>\n<head>\n  <script>\n  function dummy() {\n    return \'hello world\';\n  }\n  </script>\n</head>\n<body/>\n</html>\n', utils.Template.render(_text))
