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


class GlobalsModel(FrameContext):
    frame_ptr = models.OneToOneField(FrameContext, on_delete=models.DO_NOTHING, parent_link=True, primary_key=True)
    variables = models.JSONField(
        blank=True, null=True, default=dict,
        verbose_name='Globals', help_text='Global parameters and variables')

    class Meta:
        managed = False


class GlobalsCreateForm(CreateContextForm):
    class Meta:
        model = GlobalsModel
        fields = CreateContextForm.fields(FIELDS)
        widgets = CreateContextForm.widgets(WIDGETS)


class GlobalsUpdateForm(UpdateContextForm):
    class Meta:
        model = GlobalsModel
        fields = UpdateContextForm.fields(FIELDS)
        widgets = UpdateContextForm.widgets(WIDGETS)


class Implementation(ContextPluginImplementation):
    CAT = FrameContext.CAT_GLOBALS
    TITLE = 'Globals'
    DESCR = 'System global parameters and variables'

    Model = GlobalsModel
    CreateForm = GlobalsCreateForm
    UpdateForm = GlobalsUpdateForm

    def run(self, model, image, ctx):
        _resolvers = {'globals': context.MapResolver(model.variables)}
        return _resolvers

