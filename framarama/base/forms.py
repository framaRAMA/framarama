from django import forms
from django.conf import settings


def hiddenFieldWidget(*args, **kwargs):
    return forms.HiddenInput(*args, **kwargs)


def charFieldWidget(*args, **kwargs):
    return forms.TextInput(attrs={'class':'form-control'}, *args, **kwargs)


def booleanFieldWidget(*args, **kwargs):
    return forms.CheckboxInput(attrs={'class':'form-check-input'}, *args, **kwargs)


def textareaFieldWidget(*args, **kwargs):
    return forms.Textarea(attrs={'class':'form-control', 'style':'height:15em;'}, *args, **kwargs)


def codeareaFieldWidget(*args, **kwargs):
    return forms.Textarea(attrs={'class':'form-control', 'style':'height:25em; font-family:monospace;'}, *args, **kwargs)


def selectFieldWidget(choices, *args, **kwargs):
    return forms.Select(attrs={'class':'form-control'}, choices=choices, *args, **kwargs)


def multiChoiceFieldWidget(choices=(), *args, **kwargs):
    return forms.CheckboxSelectMultiple(attrs={'class':'form-check-input'}, choices=choices, *args, *kwargs)


def timeFieldWidget(*args, **kwargs):
    return forms.TimeInput(attrs={'class':'form-control'}, *args, **kwargs)


def passwordFieldWidget(*args, **kwargs):
    return forms.PasswordInput(attrs={'class':'form-control'}, *args, **kwargs)


def fileWidget(*args, **kwargs):
    return forms.ClearableFileInput(attrs={'class':'form-control'}, *args, **kwargs)


def generatedKeyCharFieldWidget(length=32, *args, **kwargs):
    class GenerateKeyTextInput(forms.TextInput):
        pass
    return GenerateKeyTextInput(attrs={'class':'form-control', 'generate-length':length}, *args, **kwargs)


def customSortingQueryFieldWidget(*args, **kwargs):
    if settings.FRAMARAMA['CONFIG_SORTING_EVAL_QUERY']:
        class CustomSortingQueryTextInput(forms.Textarea):
            pass
        return CustomSortingQueryTextInput(attrs={'class':'form-control', 'style':'height:15em;'}, *args, **kwargs)
    else:
        return textareaFieldWidget(*args, **kwargs)


def pathSelectorCharFieldWidget(*args, **kwargs):
    class PathSelectorTextInput(forms.TextInput):
        pass
    return PathSelectorTextInput(attrs={'class':'form-control'}, *args, **kwargs)


class BaseForm(forms.Form):

    def field_groups(self):
        return {}


class BaseModelForm(forms.ModelForm, BaseForm):
    pass


class UploadFieldForm(forms.Form):
    upload = forms.FileField(label='File', widget=fileWidget())


class BaseChainedForm(BaseForm):

    def __init__(self, forms, *args, **kwargs):
        super().__init__(self, *args, **kwargs)
        self._chain = forms
        self.is_bound = all(_form.is_bound for _form in self._chain)

    def chain(self):
        return self._chain

    def clean(self):
        for _form in self._chain:
            _form.clean()

    def is_valid(self):
        return all(_form.is_valid() for _form in self._chain)
