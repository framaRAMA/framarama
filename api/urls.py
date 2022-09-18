from django.urls import path, include
from rest_framework_extensions import routers
from rest_framework.schemas import get_schema_view

from api import views


router = routers.ExtendedDefaultRouter(trailing_slash=False)

# frames
router_frames = router.register(
  r'frames', views.FrameViewSet, basename='frame')
router_frames.register(
  r'items', views.FrameItemViewSet, basename='frame_item', parents_query_lookups=['frame'])

# displays
router_display = router.register(
  r'displays', views.DisplayViewSet, basename='display')
router_display.register(
  r'items/all', views.ItemDisplayViewSet, basename='display_item_all', parents_query_lookups=['frame__display'])
router_display.register(
  r'items/next', views.NextItemDisplayViewSet, basename='display_item_next', parents_query_lookups=['display'])
router_display.register(
  r'finishings', views.FinishingDisplayViewSet, basename='display_finishing', parents_query_lookups=['frame__display'])

urlpatterns = [
    path('', include(router.urls)),
    path('api-auth/',  include('rest_framework.urls', namespace='rest_framework')),
    path('schema/', get_schema_view(
        title="Your Project",
        description="API for all things …",
        version="1.0.0",
        urlconf='api.urls'
    ), name='openapi-schema'),
]

