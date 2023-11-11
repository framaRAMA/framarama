from django.core.exceptions import ValidationError
from django import forms

from framarama.base import forms as base
from framarama.base.models import TIMEZONE_CHOICES
from frontend import models


class LocalModeSetupForm(base.BaseModelForm):
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


class CloudModeSetupForm(base.BaseModelForm):
    cloud_status_restriction = forms.MultipleChoiceField(
        choices=models.STATUS_RESTRICTION_CHOICES,
        widget=base.multiChoiceFieldWidget())

    class Meta:
        model = models.Config
        fields = ['mode', 'cloud_server', 'cloud_display_access_key', 'cloud_status_restriction']
        widgets = {
            'mode': base.hiddenFieldWidget(),
            'cloud_server': base.charFieldWidget(),
            'cloud_display_access_key': base.charFieldWidget(),
        }


class DisplaySetupForm(base.BaseModelForm):
    class Meta:
        model = models.Config
        fields = ['sys_time_zone', 'count_items_keep', 'watermark_type', 'watermark_shift', 'watermark_scale']

        widgets = {
            'sys_time_zone': base.selectFieldWidget(choices=TIMEZONE_CHOICES),
            'count_items_keep': base.charFieldWidget(),
            'watermark_type': base.selectFieldWidget(choices=models.WATERMARKTYPE_CHOICES),
            'watermark_shift': base.charFieldWidget(),
            'watermark_scale': base.charFieldWidget(),
        }


class SoftwareSetupForm(base.BaseModelForm):
    class Meta:
        model = models.Config
        fields = ['app_update_check', 'app_update_install']

        widgets = {
            'app_update_check': base.selectFieldWidget(choices=models.APP_UPDATE_CHECK_CHOICES),
            'app_update_install': base.booleanFieldWidget(),
        }


class SoftwareDashboardCheckForm(base.BaseForm):
    url = forms.CharField(widget=base.charFieldWidget(),
        label='Remote URL', help_text='The address to fetch updates from (empty uses default)')
    username = forms.CharField(widget=base.charFieldWidget(),
        required=False,
        label='Username', help_text='Username to access URL if required')
    password = forms.CharField(widget=base.passwordFieldWidget(),
        required=False,
        label='Password', help_text='Password to access URL if required')


class SoftwareDashboardUpdateForm(base.BaseForm):
    revision = forms.CharField(widget=base.selectFieldWidget(choices=[]),
        label='Revsion', help_text='Update to the selected revision')

