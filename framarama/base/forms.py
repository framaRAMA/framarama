from django import forms


def hiddenFieldWidget(*args, **kwargs):
    return forms.HiddenInput(*args, **kwargs)


def charFieldWidget(*args, **kwargs):
    return forms.TextInput(attrs={'class':'form-control'}, *args, **kwargs)


def booleanFieldWidget(*args, **kwargs):
    return forms.CheckboxInput(attrs={'class':'form-check-input'}, *args, **kwargs)


def textareaFieldWidget(*args, **kwargs):
    return forms.Textarea(attrs={'class':'form-control', 'style':'height:15em;'}, *args, **kwargs)


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


class BaseForm(forms.Form):

    def field_groups(self):
        return {}


class BaseModelForm(forms.ModelForm, BaseForm):

    @classmethod
    def fields(cls, subclass_fields):
        fields = cls.Meta.fields.copy()
        fields.extend(subclass_fields)
        return fields

    @classmethod
    def widgets(cls, subclass_widgets):
        widgets = cls.Meta.widgets.copy()
        widgets.update(subclass_widgets)
        return widgets


