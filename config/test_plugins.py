import os
import datetime

from unittest import TestCase
from django.db import connection

from config import plugins
from config.plugins.contexts import exif
from config.plugins.finishings import shape
from config.plugins.sortings import custom
from config.plugins.sources import http


class PluginRegistryTestCase(TestCase):

    def test_all(self):
      self.assertIsNotNone(plugins.ContextPluginRegistry.all())
      self.assertIsNotNone(plugins.FinishingPluginRegistry.all())
      self.assertIsNotNone(plugins.SortingPluginRegistry.all())
      self.assertIsNotNone(plugins.SourcePluginRegistry.all())


class BasePluginRegistryTestCase():

    def _registry(self):
        return None

    def _plugin(self):
        return None

    def _plugin_instance(self, **kwargs):
        return None

    def test_get_plugin(self):
      self.assertIsNotNone(self._registry().get(self._plugin()))

    def test_get_plugin_unknown(self):
      self.assertIsNone(self._registry().get('unknown'))

    def test_get_all(self):
      _models = self._registry().get_all([
          self._plugin_instance(),
          self._plugin_instance(),
      ])
      self.assertEqual(2, len(_models))


class ContextPluginRegistryTestCase(BasePluginRegistryTestCase, TestCase):

    def _registry(self):
        return plugins.ContextPluginRegistry

    def _plugin(self):
        return 'exif'

    def _plugin_instance(self, **kwargs):
        return exif.ExifModel(plugin='exif', **kwargs)

    def test_source_get_enabled(self):
      _models = self._registry().get_enabled([
          self._plugin_instance(enabled=True),
          self._plugin_instance(enabled=False),
      ])
      self.assertEqual(1, len(_models))


class FinishingPluginRegistryTestCase(BasePluginRegistryTestCase, TestCase):

    def _registry(self):
        return plugins.FinishingPluginRegistry

    def _plugin(self):
        return 'shape'

    def _plugin_instance(self, **kwargs):
        return shape.ShapeModel(plugin='shape', **kwargs)

    def test_source_get_enabled(self):
      _models = self._registry().get_enabled([
          self._plugin_instance(enabled=True),
          self._plugin_instance(enabled=False),
      ])
      self.assertEqual(1, len(_models))


class SortingPluginRegistryTestCase(BasePluginRegistryTestCase, TestCase):

    def _registry(self):
        return plugins.SortingPluginRegistry

    def _plugin(self):
        return 'custom'

    def _plugin_instance(self, **kwargs):
        return custom.CustomModel(plugin='custom', **kwargs)

    def test_source_get_enabled(self):
      _models = self._registry().get_enabled([
          self._plugin_instance(enabled=True),
          self._plugin_instance(enabled=False),
      ])
      self.assertEqual(1, len(_models))


class SourcePluginRegistryTestCase(BasePluginRegistryTestCase, TestCase):

    def _registry(self):
        return plugins.SourcePluginRegistry

    def _plugin(self):
        return 'http'

    def _plugin_instance(self, **kwargs):
        return http.HttpModel(plugin='http', **kwargs)


