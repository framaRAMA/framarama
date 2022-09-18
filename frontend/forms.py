from django.core.exceptions import ValidationError

from framarama.base import forms as base
from frontend import models

class LocalSetupForm(base.BaseModelForm):
    class Meta:
        model = models.Config
        fields = ['mode', 'local_db_type', 'local_db_host', 'local_db_name', 'local_db_user', 'local_db_pass', 'cloud_display_access_key']
        widgets = {
          'mode': base.hiddenFieldWidget(),
          'local_db_type': base.selectFieldWidget(choices=models.DBTYPE_CHOICES),
          'local_db_host': base.charFieldWidget(),
          'local_db_name': base.charFieldWidget(),
          'local_db_user': base.charFieldWidget(),
          'local_db_pass': base.charFieldWidget(),
          'cloud_display_access_key': base.charFieldWidget(),
        }

    def clean(self):
        _data = super().clean()
        if _data.get('local_db_type') != 'local':
            if not _data.get('local_db_host'):
                self.add_error('local_db_host', ValidationError('Specify a database host'))
            if not _data.get('local_db_name'):
                self.add_error('local_db_name', ValidationError('The database name is missing'))
            if not _data.get('local_db_user'):
                self.add_error('local_db_user', ValidationError('Provide username for connection'))
            if not _data.get('local_db_pass'):
                self.add_error('local_db_pass', ValidationError('Provide password for connection'))


class CloudSetupForm(base.BaseModelForm):
    class Meta:
        model = models.Config
        fields = ['mode', 'cloud_server', 'cloud_display_access_key']
        widgets = {
            'mode': base.hiddenFieldWidget(),
            'cloud_server': base.charFieldWidget(),
            'cloud_display_access_key': base.charFieldWidget(),
        }

