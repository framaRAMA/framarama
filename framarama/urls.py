"""framarama URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from django.views.generic import base
from django.contrib.staticfiles import urls as static_urls, storage as static_storage

from rest_framework.schemas import get_schema_view


urlpatterns = [
    path('favicon.ico', base.RedirectView.as_view(url=static_storage.staticfiles_storage.url('common/icon/favicon.ico'), permanent=True)),
]
urlpatterns_api = []

if 'server' in settings.FRAMARAMA['MODES']:
    urlpatterns.append(path('config/', include('config.urls')))
    urlpatterns.append(path('admin/', admin.site.urls))
    urlpatterns_api.append(path('', include('api.urls.config')))

if 'frontend' in settings.FRAMARAMA['MODES']:
    urlpatterns.append(path('frontend/', include('frontend.urls')))
    urlpatterns_api.append(path('', include('api.urls.frontend')))


urlpatterns_api.append(path('api-auth/',  include('rest_framework.urls', namespace='rest_framework')))
urlpatterns_api.append(path('schema/', get_schema_view(
        title="framaRAMA",
        description="API",
        version="1.0.0",
        patterns=urlpatterns_api
    ), name='openapi-schema'))


urlpatterns.append(path('api/', include(urlpatterns_api)))

urlpatterns += static_urls.staticfiles_urlpatterns()

