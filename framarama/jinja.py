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


def environment(**options):
    env = Environment(**options)
    env.globals.update({
        'static': static,
        'url': reverse,
        'urle': reverse_exists,
        'nav': nav,
    })
    return env
