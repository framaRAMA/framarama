import os
import datetime

from unittest import TestCase

from config.utils import context


class ContextResolverTestCase(TestCase):

    def test_mapresolver(self):
        _context = context.MapResolver({'key': 'value', 'second':'other'})
        self.assertEqual('value', _context['key'])
        self.assertEqual('other', _context['second'])
        self.assertEqual(None, _context['missing'])

    def test_envresolver(self):
        os.environ['HOME'] = '/some/path'
        _context = context.EnvironmentResolver()
        self.assertEqual('/some/path', _context['HOME'])
        self.assertEqual(None, _context['missing'])

    def test_objectresolver(self):
        _context = context.ObjectResolver(datetime.datetime.now())
        self.assertIsNotNone(_context['hour'])
        self.assertIsNotNone(_context['minute'])
        self.assertIsNotNone(_context['second'])
        self.assertEqual(None, _context['missing'])
