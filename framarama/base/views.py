import mimetypes

from django.conf import settings
from django.shortcuts import render
from django.urls import reverse
from django.http import HttpResponse, HttpResponseRedirect
from django.utils import timezone
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin

from framarama.base import utils
from config import models


class BaseView(TemplateView):
    DEFAULT_IMAGE = utils.Filesystem.file_read('common/static/common/1x1-transparent.png')
    DEFAULT_IMAGE_MIME = 'image/png'

    def _tz(self, context):
        return settings.TIME_ZONE

    def _handle(self, callback, request, *args, **kwargs):
        _context = {}
        _context['MODES'] = settings.FRAMARAMA['MODES']
        _context.update(callback(request, *args, **kwargs))
        if '_response' in _context:
           return _context['_response']
        with utils.DateTime.zoned(self._tz(_context)):
            _result = render(request, self.template_name, _context)
        return _result

    def _get(self, request):
        return {}

    def _post(self, request):
        return {}

    def get_paginator(self, request, name, items):
        _page = request.GET.get('page{}'.format(name))
        _page_size = request.GET.get('page_size{}'.format(name), 20)
        return Paginator(items, _page_size).get_page(_page)

    def get(self, request, *args, **kwargs):
        return self._handle(self._get, request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return self._handle(self._post, request, *args, **kwargs)

    def view_name(self, request):
        return request.resolver_match.view_name

    def url(self, request):
        return request.get_full_path()

    def redirect(self, context, page=None, query=None, args=[]):
        _query = '?' + query if query else ''
        _page = page if page else self.view_name(self.request)
        context['_response'] = HttpResponseRedirect(reverse(_page, args=args) + _query)

    def response(self, context, data=None, mime=None, status=None, headers=None):
        context['_response'] = HttpResponse(data, mime if mime else 'application/octet-stream')
        if status:
            context['_response'].status_code = status
        if headers:
            for _name, _value in headers.items():
                context['_response'][_name] = _value

    def response_json(self, context, data):
        self.response(context, utils.Json.from_dict(data), 'application/json')

    def response_download(self, context, data, mime=None, filename=None):
        _ext = mimetypes.guess_extension(mime) if mime else ''
        if filename:
          _filename = filename
        else:
          _ts = utils.DateTime.utc(utils.DateTime.now(), True)
          _filename = 'download-{}'.format(str(_ts).split('.')[0])
        context['_response'] = HttpResponse(data, mime if mime else 'application/octet-stream')
        context['_response']['Content-Disposition'] = 'attachment; filename={}{}'.format(_filename, _ext)

    def response_image_default(self, context):
        self.response(context, BaseView.DEFAULT_IMAGE, BaseView.DEFAULT_IMAGE_MIME)


class BaseQuerySetMixin:

    def qs(self):
        if not hasattr(self, '_qs'):
            _user = self.request._user if hasattr(self.request, '_user') else self.request.user
            self._qs = type('', (object,), {
              'frames': (
                  _user.qs_frames if hasattr(_user, 'qs_frames') else
                  models.Frame.objects).filter(user=_user),
              'sources': (
                  _user.qs_sources if hasattr(_user, 'qs_sources') else
                  models.Source.objects).filter(frame__user=_user),
              'sourcesteps': (
                  _user.qs_sourcesteps if hasattr(_user, 'qs_source_steps') else
                  models.SourceStep.objects).filter(source__frame__user=_user),
              'sortings': (
                  _user.qs_sortings if hasattr(_user, 'qs_sortings') else
                  models.Sorting.objects).filter(frame__user=_user),
              'items': (
                  _user.qs_items if hasattr(_user, 'qs_items') else
                  models.Item.objects).filter(frame__user=_user),
              'displays': (
                  _user.qs_displays if hasattr(_user, 'qs_displays') else
                  models.Display.objects).filter(user=_user),
              'displaystatus': (
                  _user.qs_displaystatus if hasattr(_user, 'qs_displaystatus') else
                  models.DisplayStatus.objects).filter(display__user=_user),
              'displayitems': (
                  _user.qs_displayitems if hasattr(_user, 'qs_displayitems') else
                  models.DisplayItem.objects).filter(display__user=_user),
              'finishings': (
                  _user.qs_finishings if hasattr(_user, 'qs_finishings') else
                  models.Finishing.objects).filter(frame__user=_user),
              'contexts': (
                  _user.qs_contexts if hasattr(_user, 'qs_contexts') else
                  models.FrameContext.objects).filter(frame__user=_user),
              'settings': (
                  _user.qs_settings if hasattr(_user, 'qs_settings') else
                  models.Settings.objects).filter(user=_user),
            })
        return self._qs


class BaseAuthenticatedView(LoginRequiredMixin, BaseView, BaseQuerySetMixin):
    pass


