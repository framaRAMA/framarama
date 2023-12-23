import base64
import datetime

from django.templatetags.static import static
from django.utils.timezone import localtime
from django.urls import reverse

from jinja2 import Environment, Template, BaseLoader

from framarama.base import utils


def reverse_exists(*args, **kwargs):
    try:
        return reverse(*args, **kwargs)
    except:
        return None


def nav(request, page, args={}):
    if page is None:
        return False
    exists = reverse_exists(page, args=args)
    if exists is None:
        return False
    if page != 'index' and request.path.startswith(exists):
        return True
    if len(args) == 0 and page == request.resolver_match.url_name:
        return True
    return False


def date_format(value, format="%H:%M %d-%m-%y"):
    if type(value) == str:
        value = utils.DateTime.parse(value)
    return localtime(value).strftime(format)


def duration(value, parts=None, short=False, append=None):
    if type(value) == datetime.datetime:
        value = utils.DateTime.now() - value
    if value is None:
        return None
    _delta = utils.DateTime.delta_dict(value)
    _result = []
    for _part in ['days', 'hours', 'minutes']:
        if _delta[_part] and (parts is None or _part in parts):
            if short:
                _result.append('{} {}'.format(_delta[_part], _part))
                break
            else:
                _result.append('{} {}'.format(_delta[_part], _part))
    if len(_result) == 0:
        _part = 'seconds' if parts is None else parts[0]
        _result.append('{} {}'.format(_delta[_part], _part))
    return '{}{}'.format(', '.join(_result), ' ' + append if append else '')


def b64decode(value):
    return base64.b64decode(value) if value else None


def b64encode(value):
    return base64.b64encode(value).decode() if value else None


def get_attribute(value, key):
    if type(key) == str:
        if ':' in key:
            key = key.split(':')[1]
        key = key.split('.')
    if len(key) > 0:
        if key[0] == '__self__':
            return get_attribute(value, key[1:])
        elif type(value) == dict:
            value = value[key[0]]
        else:
            value = getattr(value, key[0])
        return get_attribute(value, key[1:])
    return value


def template(value, context):
    template = environment(loader=BaseLoader()).from_string(value)
    return template.render(context)


def environment(**options):
    env = Environment(**options)
    env.globals.update({
        'static': static,
        'url': reverse,
        'urle': reverse_exists,
        'nav': nav,
    })
    env.filters.update({
        'getattr': get_attribute,
        'date_format': date_format,
        'duration': duration,
        'b64decode': b64decode,
        'b64encode': b64encode,
        'template': template,
    })
    return env
