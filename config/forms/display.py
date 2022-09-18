
from config import models
from framarama.base import forms as base


class CreateDisplayForm(base.BaseModelForm):
    class Meta:
        model = models.Display
        fields = ['name', 'description', 'enabled']
        widgets = {
            'name': base.charFieldWidget(),
            'description': base.textareaFieldWidget(),
            'enabled': base.booleanFieldWidget(),
        }


class UpdateDisplayForm(base.BaseModelForm):
    class Meta:
        model = models.Display
        fields = ['name', 'description', 'enabled', 'frame']
        widgets = {
            'name': base.charFieldWidget(),
            'description': base.textareaFieldWidget(),
            'enabled': base.booleanFieldWidget(),
            'frame': base.selectFieldWidget(choices=()),
        }

    def __init__(self, *args, **kwargs):
        _user = kwargs.pop('user')
        super().__init__(*args, **kwargs)
        _frame_field = self.fields['frame']
        _frame_field.queryset=models.Frame.objects.filter(user=_user).all()


class UpdateDeviceDisplayForm(base.BaseModelForm):
    class Meta:
        model = models.Display
        fields = ['device_type', 'device_width', 'device_height']
        widgets = {
            'device_type': base.selectFieldWidget(choices=models.DEVICE_CHOICES),
            'device_width': base.charFieldWidget(),
            'device_height': base.charFieldWidget(),
        }


class UpdateTimeDisplayForm(base.BaseModelForm):
    class Meta:
        model = models.Display
        fields = ['time_on', 'time_off', 'time_change']
        widgets = {
            'time_on': base.timeFieldWidget(),
            'time_off': base.timeFieldWidget(),
            'time_change': base.timeFieldWidget(),
        }


class UpdateAccessDisplayForm(base.BaseModelForm):
    class Meta:
        model = models.Display
        fields = ['access_key']
        widgets = {
            'access_key': base.generatedKeyCharFieldWidget(length=48),
        }

