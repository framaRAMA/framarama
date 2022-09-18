
from django.shortcuts import render
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin


class BaseView(TemplateView):

    def _handle(self, callback, request, *args, **kwargs):
        _context = {}
        _context.update(callback(request, *args, **kwargs))
        if '_response' in _context:
           return _context['_response']
        return render(request, self.template_name, _context)

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


class BaseAuthenticatedView(LoginRequiredMixin, BaseView):
    pass


