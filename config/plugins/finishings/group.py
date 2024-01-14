import logging

from django.db import models

from framarama.base import forms as base
from config.models import Finishing
from config.plugins import FinishingPluginImplementation
from config.forms.frame import CreateFinishingForm, UpdateFinishingForm
from config.utils import finishing


logger = logging.getLogger(__name__)

FIELDS = [
]
WIDGETS = {
}


class GroupModel(Finishing):
    finishing_ptr = models.OneToOneField(Finishing, on_delete=models.DO_NOTHING, parent_link=True, primary_key=True)

    class Meta:
        managed = False


class GroupCreateForm(CreateFinishingForm):
    class Meta:
        model = GroupModel
        fields = CreateFinishingForm.fields(FIELDS)
        widgets = CreateFinishingForm.widgets(WIDGETS)


class GroupUpdateForm(UpdateFinishingForm):
    class Meta:
        model = GroupModel
        fields = UpdateFinishingForm.fields(FIELDS)
        widgets = UpdateFinishingForm.widgets(WIDGETS)


class Implementation(FinishingPluginImplementation):
    CAT = Finishing.CAT_GROUP
    TITLE = 'Group'
    DESCR = 'Group elements'
    
    Model = GroupModel
    CreateForm = GroupCreateForm
    UpdateForm = GroupUpdateForm
    
    def run(self, model, image, ctx):
        return image

