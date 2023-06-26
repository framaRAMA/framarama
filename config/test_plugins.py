import os
import datetime

from unittest import TestCase
from django.db import connection, models as fields

from config import plugins, models
from config.forms import frame as forms
from config.plugins.contexts import exif
from config.plugins.finishings import shape
from config.plugins.sortings import custom
from config.plugins.sources import http


class BaseTestPluginModel(models.PluginModel):
    name = fields.CharField(null=True, max_length=32)
    desc = fields.CharField(null=True, max_length=255)

    class Meta:
        managed = False

    def save(self, *args, **kwargs):
        pass


class SpecificTestPluginModel(BaseTestPluginModel):
    title = fields.CharField(null=True, max_length=32)
    votes = fields.IntegerField()
    enabled = fields.BooleanField()

    class Meta:
        managed = False


class Implementation(plugins.PluginImplementation):
    CAT = 'test'
    TITLE = 'Test'
    DESCR = 'Test plugin'

    Model = SpecificTestPluginModel
    CreateForm = forms.BasePluginForm
    UpdateForm = forms.BasePluginForm


class PluginModelTestCase(TestCase):

    def test_get_fields(self):
        _model = SpecificTestPluginModel()
        _field_names = [_field.name for _field in _model.get_fields()]
        self.assertFalse('name' in _field_names)
        self.assertFalse('desc' in _field_names)
        self.assertTrue('title' in _field_names)
        self.assertTrue('votes' in _field_names)
        self.assertTrue('enabled' in _field_names)
        self.assertFalse('plugin' in _field_names)
        self.assertFalse('plugin_config' in _field_names)

    def test_get_fields_base(self):
        _model = SpecificTestPluginModel()
        _field_names = [_field.name for _field in _model.get_fields(True)]
        self.assertTrue('name' in _field_names)
        self.assertTrue('desc' in _field_names)
        self.assertTrue('title' in _field_names)
        self.assertTrue('votes' in _field_names)
        self.assertTrue('enabled' in _field_names)
        self.assertTrue('plugin' in _field_names)
        self.assertTrue('plugin_config' in _field_names)

    def test_get_fields_model(self):
        _model = SpecificTestPluginModel()
        _field_names = [_field.name for _field in _model.get_fields(False, True)]
        self.assertFalse('name' in _field_names)
        self.assertFalse('desc' in _field_names)
        self.assertTrue('title' in _field_names)
        self.assertTrue('votes' in _field_names)
        self.assertTrue('enabled' in _field_names)
        self.assertFalse('plugin' in _field_names)
        self.assertFalse('plugin_config' in _field_names)


class PluginTestCase(TestCase):

    def _plugin(self):
        from config import test_plugins
        return plugins.Plugin('test', test_plugins)

    def test_plugin_create_model(self):
        _plugin = self._plugin()
        _model = _plugin.create_model(BaseTestPluginModel())
        self.assertIsNotNone(_model)
        self.assertEqual(None, _model.name)
        self.assertEqual(None, _model.desc)
        self.assertEqual(None, _model.title)
        self.assertEqual(None, _model.votes)
        self.assertEqual(None, _model.enabled)
        self.assertEqual('', _model.plugin)
        self.assertEqual(None, _model.plugin_config)

    def test_plugin_create_model_none(self):
        _plugin = self._plugin()
        _model = _plugin.create_model()
        self.assertIsNotNone(_model)
        self.assertEqual(None, _model.name)
        self.assertEqual(None, _model.desc)
        self.assertEqual(None, _model.title)
        self.assertEqual(None, _model.votes)
        self.assertEqual(None, _model.enabled)
        self.assertEqual('', _model.plugin)
        self.assertEqual(None, _model.plugin_config)

    def test_plugin_save_model(self):
        _model = BaseTestPluginModel()
        _plugin = self._plugin()
        _plugin.save_model(_model)

    def test_plugin_update_model(self):
        _model = BaseTestPluginModel()
        _plugin = self._plugin()
        _plugin.update_model(_model, {'name': 'Name', 'title': 'Test', 'votes': 100, 'enabled': True})
        self.assertIsNotNone(_model)
        self.assertEqual('test', _model.plugin)
        self.assertEqual('Name', _model.name)
        self.assertEqual(None, _model.desc)
        self.assertEqual({'title': 'Test', 'votes': 100, 'enabled': True}, _model.plugin_config)

    def test_plugin_update_model_ignore_unknown(self):
        _model = BaseTestPluginModel()
        _plugin = self._plugin()
        _plugin.update_model(_model, {'wrong': 'value'})
        self.assertIsNotNone(_model)
        self.assertEqual(None, _model.name)
        self.assertEqual(None, _model.desc)
        self.assertEqual({}, _model.plugin_config)
        self.assertFalse(hasattr(_model, 'wrong'))

    def test_plugin_update_model_base(self):
        _model = BaseTestPluginModel()
        _plugin = self._plugin()
        _plugin.update_model(_model, {'name': 'Name', 'plugin_config':{'title': 'Test', 'votes': 100, 'enabled': True}}, True)
        self.assertIsNotNone(_model)
        self.assertEqual('test', _model.plugin)
        self.assertEqual('Name', _model.name)
        self.assertEqual(None, _model.desc)
        self.assertEqual({'title': 'Test', 'votes': 100, 'enabled': True}, _model.plugin_config)

    def test_plugin_update_model_base_ignore_unknown(self):
        _model = BaseTestPluginModel()
        _plugin = self._plugin()
        _plugin.update_model(_model, {'wrong': 'value', 'plugin_config':{'wrong': 'value'}}, True)
        self.assertIsNotNone(_model)
        self.assertEqual(None, _model.name)
        self.assertEqual(None, _model.desc)
        self.assertEqual({}, _model.plugin_config)
        self.assertFalse(hasattr(_model, 'wrong'))


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



