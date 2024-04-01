import logging

from django.db import models
from django.template import Context, Template
from django.conf import settings

from framarama.base import forms as base
from config.models import FrameContext
from config.plugins import ContextPluginImplementation
from config.forms.frame import CreateContextForm, UpdateContextForm
from config.utils import context


logger = logging.getLogger(__name__)

FIELDS = [
    'variables',
]
WIDGETS = {
    'variables': base.textareaFieldWidget(),
}


class VariablesModel(FrameContext):
    frame_ptr = models.OneToOneField(FrameContext, on_delete=models.DO_NOTHING, parent_link=True, primary_key=True)
    variables = models.JSONField(
        blank=True, null=True, default=dict,
        verbose_name='Variables', help_text='Key/value pairs to provied as global variables')

    class Meta:
        managed = False


class VariablesCreateForm(CreateContextForm):
    class Meta:
        model = VariablesModel
        fields = CreateContextForm.fields(FIELDS)
        widgets = CreateContextForm.widgets(WIDGETS)


class VariablesUpdateForm(UpdateContextForm):
    class Meta:
        model = VariablesModel
        fields = UpdateContextForm.fields(FIELDS)
        widgets = UpdateContextForm.widgets(WIDGETS)


class Implementation(ContextPluginImplementation):
    CAT = FrameContext.CAT_VARS
    TITLE = 'Variables'
    DESCR = 'Global variables'

    Model = VariablesModel
    CreateForm = VariablesCreateForm
    UpdateForm = VariablesUpdateForm

    def run(self, model, image, ctx):
        _resolvers = {'globals': context.EvaluatedResolver(ctx, context.MapResolver(model.variables))}
        return _resolvers

