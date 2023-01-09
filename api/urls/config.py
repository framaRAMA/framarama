from django.urls import path, include
from rest_framework import routers
from rest_framework.schemas import get_schema_view

from api.views import config as views


router = routers.DefaultRouter(trailing_slash=False)

router.register('frames', views.FrameViewSet, 'frame')
router.register('frames/(?P<frame_id>[0-9]+)/items', views.FrameItemViewSet, 'frame_item')

router.register('displays', views.DisplayViewSet, 'display')
router.register('displays/(?P<display_id>[0-9]+)/items/all', views.ItemDisplayViewSet, 'display_item_all')
router.register('displays/(?P<display_id>[0-9]+)/items/next', views.NextItemDisplayViewSet, 'display_item_next')
router.register('displays/(?P<display_id>[0-9]+)/finishings', views.FinishingDisplayViewSet, 'display_item_next')
router.register('displays/(?P<display_id>[0-9]+)/status', views.StatusDisplayViewSet, 'display_status')

urlpatterns = [
    path('', include(router.urls)),
    path('api-auth/',  include('rest_framework.urls', namespace='rest_framework')),
    path('schema/', get_schema_view(
        title="Your Project",
        description="API for config system",
        version="1.0.0",
        urlconf='api.urls.config'
    ), name='openapi-schema'),
]

