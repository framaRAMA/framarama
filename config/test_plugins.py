import os
import datetime

from unittest import TestCase
from django import forms
from django.db import connection, models as fields

from framarama.base import forms as base
from framarama.base.models import PluginModel
from config import plugins, models
from config.forms.base import BasePluginForm
from config.forms.frame import ContextForm
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
        return exif.ExifForm.Meta.model(plugin=self._plugin(), **kwargs)

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
        return shape.ShapeForm.Meta.model(plugin=self._plugin(), **kwargs)

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
        return custom.CustomForm.Meta.model(plugin=self._plugin(), **kwargs)

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
        return http.HttpForm.Meta.model(plugin=self._plugin(), **kwargs)


class GeoContextPluginTestCase(TestCase):

  def test_empty(self):
      _plugin = plugins.ContextPluginRegistry.get('geo')
      self.assertEquals({}, _plugin.impl()._geo({}))

  def test_only_lat(self):
      _plugin = plugins.ContextPluginRegistry.get('geo')
      self.assertEquals({}, _plugin.impl()._geo({
          'gpslatituderef': 'N',
          'gpslatitude': '49/1, 28/1, 50264282/1000000',
      }))

  def test_only_long(self):
      _plugin = plugins.ContextPluginRegistry.get('geo')
      self.assertEquals({}, _plugin.impl()._geo({
          'gpslongituderef': 'N',
          'gpslongitude': '8/1, 15/1, 50264282/1000000',
      }))

  def test_only_latlong(self):
      _plugin = plugins.ContextPluginRegistry.get('geo')
      self.assertEquals({
          'lat': 49.48062896722222,
          'long': 8.263962300555555
      }, _plugin.impl()._geo({
          'gpslatituderef': 'N',
          'gpslatitude': '49/1, 28/1, 50264282/1000000',
          'gpslongituderef': 'N',
          'gpslongitude': '8/1, 15/1, 50264282/1000000',
      }))

  def test_only_latlong_whitespace(self):
      _plugin = plugins.ContextPluginRegistry.get('geo')
      self.assertEquals({
          'lat': 49.48062896722222,
          'long': 8.263962300555555
      }, _plugin.impl()._geo({
          'gpslatituderef': 'N',
          'gpslatitude': '49/1 28/1 50264282/1000000',
          'gpslongituderef': 'N',
          'gpslongitude': '8/1 15/1 50264282/1000000',
      }))

  def test_only_latlong_partial(self):
      _plugin = plugins.ContextPluginRegistry.get('geo')
      self.assertEquals({
          'lat': 49.46666666666667,
          'long': 8.25
      }, _plugin.impl()._geo({
          'gpslatituderef': 'N',
          'gpslatitude': '49/1, 28/1',
          'gpslongituderef': 'N',
          'gpslongitude': '8/1, 15/1',
      }))

