import logging

from config.models import Finishing
from config.plugins import FinishingPluginImplementation
from config.forms.frame import FinishingForm


logger = logging.getLogger(__name__)


class GroupForm(FinishingForm):

    dependencies = {}

    class Meta(FinishingForm.Meta):
        pass


class Implementation(FinishingPluginImplementation):
    CAT = Finishing.CAT_GROUP
    TITLE = 'Group'
    DESCR = 'Group elements'
    
    Form = GroupForm
    
    def run(self, model, config, image, ctx):
        return image

