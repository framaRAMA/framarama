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


class ContextTestCase(TestCase):

    def test_context_evaluate_none(self):
        _context = context.Context()
        self.assertIsNone(_context.evaluate(None))

    def test_context_evaluate_no_resolver(self):
        _context = context.Context()
        self.assertEqual('hello world', _context.evaluate("hello world"))

    def test_context_evaluate_no_resolver_key_missing(self):
        _context = context.Context()
        with self.assertRaises(NameError):
            self.assertEqual('', _context.evaluate("{missing}"))

    def test_context_evaluate_keys(self):
        _context = context.Context()
        _context.set_resolver('test', context.MapResolver({'key': 'value', 'second':'other'}))
        self.assertEqual('value-other', _context.evaluate("{test['key']}-{test['second']}"))

    def test_context_evaluate_quotes(self):
        _context = context.Context()
        self.assertEqual('"some quotes"', _context.evaluate('"some quotes"'))
        self.assertEqual("'some quotes'", _context.evaluate("'some quotes'"))

    def test_context_evaluate_long(self):
        _context = context.Context()
        _text = """
hello world
"""
        self.assertEqual("\nhello world\n", _context.evaluate(_text))

    def test_context_evaluate_long_quotes(self):
        _context = context.Context()
        _text = """
hello \"\"\" world \"\"\"
"""
        self.assertEqual('\nhello """ world """\n', _context.evaluate(_text))

    def test_context_evaluate_long_html(self):
        _context = context.Context()
        _text = """
<html>
<body>
  <a href="http://github.com/framarama/">framaRAMA</a>
</body>
</html>
"""
        self.assertEqual('\n<html>\n<body>\n  <a href="http://github.com/framarama/">framaRAMA</a>\n</body>\n</html>\n', _context.evaluate(_text))

    def test_context_evaluate_long_script(self):
        _context = context.Context()
        _text = """
<html>
<head>
  <script>
  function dummy() {{
    return 'hello world';
  }}
  </script>
</head>
<body/>
</html>
"""
        self.assertEqual('\n<html>\n<head>\n  <script>\n  function dummy() {\n    return \'hello world\';\n  }\n  </script>\n</head>\n<body/>\n</html>\n', _context.evaluate(_text))


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
