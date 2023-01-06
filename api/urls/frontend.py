from django.urls import path, include
from rest_framework import routers
from rest_framework.schemas import get_schema_view

from api.views import frontend as views


router = routers.DefaultRouter(trailing_slash=False)

router.register('display/overview', views.OverviewDisplayView, 'display_overview')
router.register('display/status', views.StatusDisplayView, 'display_status')
router.register('display/items', views.ItemsDisplayView, 'display_items')
router.register('display/screen', views.ScreenDisplayView, 'display_screen')
router.register('display/screen/switch/(?P<state>(on|off))', views.SwitchScreenDisplayView, 'display_screen_switch')

urlpatterns = [
    path('', include(router.urls)),
    path('api-auth/',  include('rest_framework.urls', namespace='rest_framework')),
    path('schema/', get_schema_view(
        title="Your Project",
        description="API for all things …",
        version="1.0.0",
        urlconf='api.urls.frontend'
    ), name='openapi-schema'),
]

