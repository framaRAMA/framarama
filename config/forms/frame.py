
from config import models
from config.forms.base import BasePluginForm
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
        fields = ['name']
        widgets = {
            'name': base.charFieldWidget(),
        }


class UpdateSourceForm(base.BaseModelForm):
    class Meta:
        model = models.Source
        fields = ['name', 'map_item_id_ext', 'map_item_url', 'map_item_date_creation', 'map_item_meta']
        widgets = {
            'name': base.charFieldWidget(),
            'map_item_id_ext': base.charFieldWidget(),
            'map_item_url': base.charFieldWidget(),
            'map_item_date_creation': base.charFieldWidget(),
            'map_item_meta': base.textareaFieldWidget(),
        }
    def field_groups(self):
        return {
            'default': {
                'title': 'Source',
                'fields': ['name'],
            },
            'mapping': {
                'title': 'Result to item mapping',
                'fields': ['map_item_id_ext', 'map_item_url', 'map_item_date_creation', 'map_item_meta'],
            }
        }


class CreateSourceStepForm(BasePluginForm):
    class Meta:
        model = models.SourceStep
        fields = ['title', 'description', 'instance', 'data_in', 'mime_in', 'merge_in', 'data_out', 'mime_out', 'loop_out']
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
    def field_groups(self):
        return self._field_groups(CreateSourceStepForm.Meta.fields)


class UpdateSourceStepForm(BasePluginForm):
    class Meta:
        model = models.SourceStep
        fields = ['title', 'description', 'instance', 'data_in', 'mime_in', 'merge_in', 'data_out', 'mime_out', 'loop_out']
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
    def field_groups(self):
        return self._field_groups(UpdateSourceStepForm.Meta.fields)


class CreateSortingForm(BasePluginForm):
    class Meta:
        model = models.Sorting
        fields = ['title', 'weight', 'enabled']
        widgets = {
            'title': base.charFieldWidget(),
            'weight': base.charFieldWidget(),
            'enabled': base.booleanFieldWidget(),
        }
    def field_groups(self):
        return self._field_groups(CreateSortingForm.Meta.fields)


class UpdateSortingForm(BasePluginForm):
    class Meta:
        model = models.Sorting
        fields = ['title', 'weight', 'enabled']
        widgets = {
            'title': base.charFieldWidget(),
            'weight': base.charFieldWidget(),
            'enabled': base.booleanFieldWidget(),
        }
    def field_groups(self):
        return self._field_groups(UpdateSortingForm.Meta.fields)


class CreateFinishingForm(BasePluginForm):
    class Meta:
        model = models.Finishing
        fields = ['title', 'image_in', 'image_out', 'color_stroke', 'color_fill', 'color_alpha', 'stroke_width', 'enabled']
        widgets = {
            'title': base.charFieldWidget(),
            'image_in': base.charFieldWidget(),
            'image_out': base.charFieldWidget(),
            'color_stroke': base.charFieldWidget(),
            'color_fill': base.charFieldWidget(),
            'color_alpha': base.charFieldWidget(),
            'stroke_width': base.charFieldWidget(),
            'enabled': base.booleanFieldWidget(),
        }
    def field_groups(self):
        return self._field_groups(CreateFinishingForm.Meta.fields)

    def field_depencies(self):
        return {
            
        }


class UpdateFinishingForm(BasePluginForm):
    class Meta:
        model = models.Finishing
        fields = ['title', 'image_in', 'image_out', 'color_stroke', 'color_fill', 'color_alpha', 'stroke_width', 'enabled']
        widgets = {
            'title': base.charFieldWidget(),
            'image_in': base.charFieldWidget(),
            'image_out': base.charFieldWidget(),
            'color_stroke': base.charFieldWidget(),
            'color_fill': base.charFieldWidget(),
            'color_alpha': base.charFieldWidget(),
            'stroke_width': base.charFieldWidget(),
            'enabled': base.booleanFieldWidget(),
        }
    def field_groups(self):
        return self._field_groups(UpdateFinishingForm.Meta.fields)



