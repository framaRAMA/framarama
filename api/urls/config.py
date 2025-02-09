from django.urls import path, include
from rest_framework import routers

from api.views import config as views


router = routers.DefaultRouter(trailing_slash=False)

router.register('frames', views.FrameViewSet, 'frame')
router.register('frames/(?P<frame_id>[0-9]+)/items', views.FrameItemViewSet, 'frame_item')

router.register('displays', views.DisplayViewSet, 'display')
router.register('displays/(?P<display_id>[0-9]+)/items/all', views.ItemDisplayViewSet, 'display_item_all')
router.register('displays/(?P<display_id>[0-9]+)/items/hits', views.HitItemDisplayViewSet, 'display_item_hit')
router.register('displays/(?P<display_id>[0-9]+)/items/next', views.NextItemDisplayViewSet, 'display_item_next')
router.register('displays/(?P<display_id>[0-9]+)/finishings', views.FinishingDisplayViewSet, 'display_finishing')
router.register('displays/(?P<display_id>[0-9]+)/contexts', views.ContextDisplayViewSet, 'display_context')
router.register('displays/(?P<display_id>[0-9]+)/status', views.StatusDisplayViewSet, 'display_status')

router.register('settings/all', views.SettingsViewSet, 'settings_list')
router.register('settings/(?P<category>[a-z]+)', views.CategorySettingsViewSet, 'settings_category_list')

urlpatterns = [
    path('', include(router.urls)),
]

