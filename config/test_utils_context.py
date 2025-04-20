import os
import datetime

from unittest import TestCase

from config.utils import context


class ResultValueTestCase(TestCase):

    def test_as_str(self):
        self.assertIsNone(context.ResultValue(None).as_str())
        self.assertEqual('hello world', context.ResultValue('hello world').as_str())

    def test_as_str_int(self):
        self.assertEqual('1', context.ResultValue(1).as_str())

    def test_as_str_float(self):
        self.assertEqual('1.4', context.ResultValue(1.4).as_str())

    def test_as_str_bool(self):
        self.assertEqual('true', context.ResultValue(True).as_str())
        self.assertEqual('false', context.ResultValue(False).as_str())

    def test_as_int(self):
        self.assertIsNone(context.ResultValue(None).as_int())
        self.assertEqual(1, context.ResultValue(1).as_int())

    def test_as_int_str(self):
        self.assertIsNone(context.ResultValue('').as_int())
        self.assertEqual(1, context.ResultValue('1').as_int())

    def test_as_int_float(self):
        self.assertEqual(1, context.ResultValue(1.4).as_int())
        self.assertEqual(1, context.ResultValue(1.6).as_int())

    def test_as_int_bool(self):
        self.assertEqual(1, context.ResultValue(True).as_int())
        self.assertEqual(0, context.ResultValue(False).as_int())

    def test_as_float(self):
        self.assertIsNone(context.ResultValue(None).as_float())
        self.assertEqual(1.5, context.ResultValue(1.5).as_float())

    def test_as_float_str(self):
        self.assertIsNone(context.ResultValue('').as_float())
        self.assertEqual(2.2, context.ResultValue('2.2').as_float())

    def test_as_float_int(self):
        self.assertEqual(1.0, context.ResultValue(1).as_float())

    def test_as_float_bool(self):
        self.assertEqual(1.0, context.ResultValue(True).as_float())
        self.assertEqual(0.0, context.ResultValue(False).as_float())

    def test_as_bool(self):
        self.assertEqual(True, context.ResultValue(True).as_bool())
        self.assertEqual(False, context.ResultValue(False).as_bool())

    def test_as_bool_str(self):
        self.assertEqual(True, context.ResultValue('true').as_bool())
        self.assertEqual(False, context.ResultValue('false').as_bool())
        self.assertEqual(True, context.ResultValue('t').as_bool())
        self.assertEqual(False, context.ResultValue('f').as_bool())
        self.assertEqual(True, context.ResultValue('1').as_bool())
        self.assertEqual(False, context.ResultValue('0').as_bool())
        self.assertEqual(True, context.ResultValue('yes').as_bool())
        self.assertEqual(False, context.ResultValue('no').as_bool())
        self.assertEqual(True, context.ResultValue('y').as_bool())
        self.assertEqual(False, context.ResultValue('n').as_bool())

    def test_str_concat(self):
        self.assertEqual("Test string", "Test " + context.ResultValue('string'))

    def test_str_concat_none(self):
        self.assertEqual("Test ", "Test " + context.ResultValue(None))

    def test_none(self):
        self.assertTrue(context.ResultValue(None) == None)
        #self.assertIsNone(context.ResultValue(None))

    def test_add(self):
        self.assertEqual(10, context.ResultValue(5)+context.ResultValue(5))
        self.assertEqual(10, context.ResultValue(5)+5)
        self.assertEqual(10, 5+context.ResultValue(5))

    def test_sub(self):
        self.assertEqual(5, context.ResultValue(10)-context.ResultValue(5))
        self.assertEqual(5, context.ResultValue(10)-5)
        self.assertEqual(5, 10-context.ResultValue(5))

    def test_mul(self):
        self.assertEqual(50, context.ResultValue(10)*context.ResultValue(5))
        self.assertEqual(50, context.ResultValue(10)*5)
        self.assertEqual(50, 10*context.ResultValue(5))

    def test_truediv(self):
        self.assertEqual(2, context.ResultValue(10)/context.ResultValue(5))
        self.assertEqual(2, context.ResultValue(10)/5)
        self.assertEqual(2, 10/context.ResultValue(5))

    def test_floordiv(self):
        self.assertEqual(3, context.ResultValue(10)//context.ResultValue(3))
        self.assertEqual(3, context.ResultValue(10)//3)
        self.assertEqual(3, 10//context.ResultValue(3))

    def test_mod(self):
        self.assertEqual(0, context.ResultValue(10)%context.ResultValue(5))
        self.assertEqual(0, context.ResultValue(10)%5)
        self.assertEqual(0, 10%context.ResultValue(5))

    def test_pow(self):
        self.assertEqual(100000, context.ResultValue(10)**context.ResultValue(5))
        self.assertEqual(100000, context.ResultValue(10)**5)
        self.assertEqual(100000, 10**context.ResultValue(5))


class ContextTestCase(TestCase):

    def test_context_evaluate_keys(self):
        _context = context.Context()
        _context.set_resolver('test', context.MapResolver({'key': 'value', 'second':'other'}))
        self.assertEqual('value-other', _context.evaluate("{{test['key']}}-{{test['second']}}"))

    def test_context_evaluate_slice(self):
        _context = context.Context()
        _context.set_resolver('test', context.MapResolver({'list': [1,2,3,4, 5, 6, 7, 8, 9, 10]}))
        self.assertEqual('2468', _context.evaluate('{{(test.list)[1:8:2]|join}}'))

    def test_context_evaluate_split(self):
        _context = context.Context()
        _context.set_resolver('test', context.MapResolver({'key': 'this is a test'}))
        self.assertEqual('this', _context.evaluate('{{test.key|split|first}}'))

    def test_context_evaluate_keys(self):
        _context = context.Context()
        _context.set_resolver('test', context.MapResolver({'key': {'a':'b', 'c':'d', 'e':'f', 'h':'i'}}))
        self.assertEqual('aceh', _context.evaluate('{{test.key|keys|join}}'))


class ContextResolverTestCase(TestCase):

    def test_mapresolver(self):
        _context = context.MapResolver({'key': 'value', 'second':'other'})
        self.assertEqual('value', _context['key'])
        self.assertEqual('value', _context.key)
        self.assertEqual('other', _context['second'])
        self.assertEqual('other', _context.second)
        self.assertEqual(None, _context['missing'])
        self.assertEqual(None, _context.missing)
        self.assertEqual(None, _context['missing']['missing'])
        self.assertEqual(None, _context.missing.missing)

    def test_envresolver(self):
        os.environ['HOME'] = '/some/path'
        _context = context.EnvironmentResolver()
        self.assertEqual('/some/path', _context['HOME'])
        self.assertEqual('/some/path', _context.HOME)
        self.assertEqual(None, _context['missing'])
        self.assertEqual(None, _context.missing)
        self.assertEqual(None, _context['missing']['missing'])
        self.assertEqual(None, _context.missing.missing)

    def test_objectresolver(self):
        _context = context.ObjectResolver(datetime.datetime.now())
        self.assertIsNotNone(_context['hour'])
        self.assertIsNotNone(_context.hour)
        self.assertIsNotNone(_context['minute'])
        self.assertIsNotNone(_context.minute)
        self.assertIsNotNone(_context['second'])
        self.assertIsNotNone(_context.second)
        self.assertEqual(None, _context['missing'])
        self.assertEqual(None, _context.missing)
        self.assertEqual(None, _context['missing']['missing'])
        self.assertEqual(None, _context.missing.missing)

    def text_evalresolver(self):
        _ctx = context.Context()
        _ctx.set_resolver('other', context.MapResolver({'value': 'test'}))
        _context = context.EvaluatedResolver(_ctx, context.MapResolver({'key': '{{other.value}}'}))
        self.assertEqual('test', _context.key)

    def test_resolve_key_punctation(self):
        _context = context.MapResolver({'key': 'value', 'second':{'key1':'val1', 'key2':'key2'}})
        self.assertIsNotNone(_context['key'])
        self.assertIsNotNone(_context['second']['key1'])
        self.assertIsNotNone(_context.second.key1)
        self.assertIsNotNone(_context['second']['key2'])
        self.assertIsNotNone(_context.second.key2)
        self.assertEqual(None, _context['second']['key3'])
        self.assertEqual(None, _context.second.key3)
