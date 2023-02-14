import base64

from django.templatetags.static import static
from django.urls import reverse

from jinja2 import Environment


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
    return value.strftime(format)


def b64decode(value):
    return base64.b64decode(value).encode()


def b64encode(value):
    return base64.b64encode(value).decode()


def get_attribute(value, key):
    if type(key) == str:
        key = key.split('.')
    if len(key) > 0:
        if type(value) == dict:
            value = value[key[0]]
        else:
            value = getattr(value, key[0])
        return get_attribute(value, key[1:])
    return value


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
        'b64decode': b64decode,
        'b64encode': b64encode,
    })
    return env
