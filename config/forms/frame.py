import json
import jinja2

from django import forms
from django.core.exceptions import ValidationError

from config import models
from config.forms.base import BasePluginForm, TreeBasePluginForm
from framarama.base import forms as base


class CreateFrameForm(base.BaseModelForm):
    class Meta:
        model = models.Frame
        fields = ['name', 'description', 'enabled']
        widgets = {
            'name': base.charFieldWidget(),
            'description': base.textareaFieldWidget(),
            'enabled': base.booleanFieldWidget(),
        }


class UpdateFrameForm(base.BaseModelForm):
    class Meta:
        model = models.Frame
        fields = ['name', 'description', 'enabled']
        widgets = {
            'name': base.charFieldWidget(),
            'description': base.textareaFieldWidget(),
            'enabled': base.booleanFieldWidget(),
        }


class CreateSourceForm(base.BaseModelForm):
    class Meta:
        model = models.Source
        fields = ['name', 'map_item_url']
        widgets = {
            'name': base.charFieldWidget(),
            'map_item_url': base.charFieldWidget(),
        }
    def field_groups(self):
        return {
            'default': {
                'title': 'Source',
                'fields': ['name'],
            },
            'mapping': {
                'title': 'Result to item mapping',
                'fields': ['map_item_url'],
            }
        }


class UpdateSourceForm(base.BaseModelForm):
    class Meta:
        model = models.Source
        fields = ['name', 'update_interval', 'map_item_id_ext', 'map_item_url', 'map_item_date_creation', 'map_item_meta']
        widgets = {
            'name': base.charFieldWidget(),
            'update_interval': base.selectFieldWidget(choices=models.SOURCE_UPDATE_INTERVAL_CHOICES),
            'map_item_id_ext': base.charFieldWidget(),
            'map_item_url': base.charFieldWidget(),
            'map_item_date_creation': base.charFieldWidget(),
            'map_item_meta': base.textareaFieldWidget(),
        }
    def field_groups(self):
        return {
            'default': {
                'title': 'Source',
                'fields': ['name', 'update_interval'],
            },
            'mapping': {
                'title': 'Result to item mapping',
                'fields': ['map_item_id_ext', 'map_item_url', 'map_item_date_creation', 'map_item_meta'],
            }
        }


class SourceStepForm(BasePluginForm):
    class Meta:
        model = models.SourceStep
        fields = []
        untangled_fields = ['title', 'description', 'instance', 'data_in', 'mime_in', 'merge_in', 'data_out', 'mime_out', 'loop_out']
        widgets = {
            'title': base.charFieldWidget(),
            'description': base.textareaFieldWidget(),
            'instance': base.charFieldWidget(),
            'data_in': base.charFieldWidget(),
            'mime_in': base.selectFieldWidget(choices=models.MIME_CHOICES),
            'merge_in': base.booleanFieldWidget(),
            'data_out': base.charFieldWidget(),
            'mime_out': base.selectFieldWidget(choices=models.MIME_CHOICES),
            'loop_out': base.booleanFieldWidget(),
        }


class SortingForm(BasePluginForm):
    class Meta:
        model = models.Sorting
        fields = []
        untangled_fields = ['title', 'weight', 'enabled']
        widgets = {
            'title': base.charFieldWidget(),
            'weight': base.charFieldWidget(),
            'enabled': base.booleanFieldWidget(),
        }


class FinishingForm(TreeBasePluginForm):
    class Meta:
        model = models.Finishing
        fields = []
        untangled_fields = ['title', 'image_in', 'image_out', 'enabled']
        widgets = {
            'title': base.charFieldWidget(),
            'image_in': base.charFieldWidget(),
            'image_out': base.charFieldWidget(),
            'enabled': base.booleanFieldWidget(),
        }

    def clean(self):
        _data = super().clean()
        for _name, _value in _data.items():
            if _value is None or type(_value) != str:
                continue
            try:
                jinja2.Environment().from_string(_value)
            except jinja2.exceptions.TemplateSyntaxError as e:
                raise ValidationError('Invalid template in {}: {}'.format(_name, e))
        return _data


class RawEditFinishingForm(base.BaseForm):
    class PrettyJSONEncoder(json.JSONEncoder):
        def __init__(self, *args, indent, sort_keys, **kwargs):
            super().__init__(*args, indent=3, **kwargs)

    config = forms.JSONField(encoder=PrettyJSONEncoder, widget=base.codeareaFieldWidget())


class ContextForm(BasePluginForm):
    class Meta:
        model = models.FrameContext
        fields = []
        untangled_fields = ['name', 'enabled']
        widgets = {
            'name': base.charFieldWidget(),
            'enabled': base.booleanFieldWidget(),
        }


