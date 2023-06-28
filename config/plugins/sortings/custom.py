import logging

from django.db import models

from framarama.base import forms as base
from config.models import Sorting
from config.plugins import SortingPluginImplementation
from config.forms.frame import CreateSortingForm, UpdateSortingForm


logger = logging.getLogger(__name__)

FIELDS = [
    'code',
]
WIDGETS = {
    'code': base.customSortingQueryFieldWidget(),
}

class CustomModel(Sorting):
    sorting_ptr = models.OneToOneField(Sorting, on_delete=models.DO_NOTHING, parent_link=True, primary_key=True)
    code = models.TextField(
        verbose_name='Query', help_text='Custom query to execute to generate a rank value')

    class Meta:
        managed = False


class CustomCreateForm(CreateSortingForm):
    class Meta:
        model = CustomModel
        fields = CreateSortingForm.fields(FIELDS)
        widgets = CreateSortingForm.widgets(WIDGETS)


class CustomUpdateForm(UpdateSortingForm):
    class Meta:
        model = CustomModel
        fields = UpdateSortingForm.fields(FIELDS)
        widgets = UpdateSortingForm.widgets(WIDGETS)


class Implementation(SortingPluginImplementation):
    CAT = Sorting.CAT_CUSTOM
    TITLE = 'Custom'
    DESCR = 'Specify a custom query'
    
    Model = CustomModel
    CreateForm = CustomCreateForm
    UpdateForm = CustomUpdateForm
    
    def run(self, model, context):
        return model.code


