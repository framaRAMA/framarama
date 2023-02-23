from django.urls import path, include

from config.views import LoginView, LogoutView, IndexView
from config.views import frame, display

urlpatterns = [
    path('accounts/login', LoginView.as_view()),
    path('accounts/logout', LogoutView.as_view(), name='logout'),

    path('', IndexView.as_view(), name='index'),
    path('frames', frame.ListFrameView.as_view(), name='frame_list'),
    path('frames/create', frame.CreateFrameView.as_view(), name='frame_create'),
    path('frames/<int:frame_id>/info', frame.ViewInfoFrameView.as_view(), name='frame_info'),
    path('frames/<int:frame_id>/edit', frame.UpdateGeneralFrameView.as_view(), name='frame_edit'),

    path('frames/<int:frame_id>/sources', frame.RedirectSourceFrameView.as_view(), name='frame_source_list'),
    path('frames/<int:frame_id>/sources/create', frame.CreateSourceFrameView.as_view(), name='frame_source_create'),

    path('frames/<int:frame_id>/sources/<int:source_id>', frame.RedirectInfoSourceFrameView.as_view(), name='frame_source'),
    path('frames/<int:frame_id>/sources/<int:source_id>/info', frame.ViewInfoSourceFrameView.as_view(), name='frame_source_info'),
    path('frames/<int:frame_id>/sources/<int:source_id>/action', frame.ActionSourceFrameView.as_view(), name='frame_source_action'),
    path('frames/<int:frame_id>/sources/<int:source_id>/edit', frame.UpdateSourceFrameView.as_view(), name='frame_source_edit'),
    path('frames/<int:frame_id>/sources/<int:source_id>/items', frame.ItemsSourceFrameView.as_view(), name='frame_source_images'),
    path('frames/<int:frame_id>/sources/<int:source_id>/items/<int:item_id>/thumbnail', frame.ThumbnailItemFrameView.as_view(), name='frame_source_image_thumbnail'),

    path('frames/<int:frame_id>/sources/<int:source_id>/steps', frame.ListStepSourceFrameView.as_view(), name='frame_source_step_list'),
    path('frames/<int:frame_id>/sources/<int:source_id>/steps/create?plugin=<str:plugin>', frame.CreateStepSourceFrameView.as_view(), name='frame_source_step_create'),
    path('frames/<int:frame_id>/sources/<int:source_id>/steps/<int:step_id>', frame.UpdateStepSourceFrameView.as_view(), name='frame_source_step_edit'),
    path('frames/<int:frame_id>/sources/<int:source_id>/steps/<int:step_id>/action', frame.ActionStepSourceFrameView.as_view(), name='frame_source_step_action'),

    path('frames/<int:frame_id>/sortings', frame.ListSortingFrameView.as_view(), name='frame_sorting_list'),
    path('frames/<int:frame_id>/sortings/create?plugin=<str:plugin>', frame.CreateSortingFrameView.as_view(), name='frame_sorting_create'),
    path('frames/<int:frame_id>/sortings/<int:sorting_id>/edit', frame.UpdateSortingFrameView.as_view(), name='frame_sorting_edit'),
    path('frames/<int:frame_id>/sortings/<int:sorting_id>/action', frame.ActionSortingFrameView.as_view(), name='frame_sorting_action'),

    path('frames/<int:frame_id>/finishings', frame.ListFinishingFrameView.as_view(), name='frame_finishing_list'),
    path('frames/<int:frame_id>/finishings/create?plugin=<str:plugin>', frame.CreateFinishingFrameView.as_view(), name='frame_finishing_create'),
    path('frames/<int:frame_id>/finishings/<int:finishing_id>/edit', frame.UpdateFinishingFrameView.as_view(), name='frame_finishing_edit'),
    path('frames/<int:frame_id>/finishings/<int:finishing_id>/action', frame.ActionFinishingFrameView.as_view(), name='frame_finishing_action'),
    path('frames/<int:frame_id>/contexts', frame.ListContextFrameView.as_view(), name='frame_context_list'),
    path('frames/<int:frame_id>/contexts/create?plugin=<str:plugin>', frame.CreateContextFrameView.as_view(), name='frame_context_create'),
    path('frames/<int:frame_id>/contexts/<int:context_id>/edit', frame.UpdateContextFrameView.as_view(), name='frame_context_edit'),
    path('frames/<int:frame_id>/contexts/<int:context_id>/action', frame.ActionContextFrameView.as_view(), name='frame_context_action'),

    path('frames/<int:frame_id>/images/preview', frame.PreviewImageFrameView.as_view(), name='frame_image_preview'),

    path('displays', display.ListDisplayView.as_view(), name='display_list'),
    path('displays/create', display.CreateDisplayView.as_view(), name='display_create'),
    path('displays/<int:display_id>/overview', display.OverviewDisplayView.as_view(), name='display_overview'),
    path('displays/<int:display_id>/items/<int:item_id>/thumbnail', display.ThumbnailItemDisplayView.as_view(), name='display_item_thumbnail'),
    path('displays/<int:display_id>/info', display.ViewInfoDisplayView.as_view(), name='display_info'),
    path('displays/<int:display_id>/info/edit', display.UpdateDisplayView.as_view(), name='display_edit'),
    path('displays/<int:display_id>/device', display.ViewDeviceDisplayView.as_view(), name='display_device'),
    path('displays/<int:display_id>/device/edit', display.UpdateDeviceDisplayView.as_view(), name='display_device_edit'),
    path('displays/<int:display_id>/time', display.ViewTimeDisplayView.as_view(), name='display_time'),
    path('displays/<int:display_id>/time/edit', display.UpdateTimeDisplayView.as_view(), name='display_time_edit'),
    path('displays/<int:display_id>/access', display.ViewAccessDisplayView.as_view(), name='display_access'),
    path('displays/<int:display_id>/access/edit', display.UpdateAccessDisplayView.as_view(), name='display_access_edit'),
]
