from django.urls import path, include

from frontend import views

urlpatterns = [
    path('', views.SetupView.as_view(), name='fe_index'),
    path('setup/mode/local', views.LocalModeSetupView.as_view(), name='fe_setup_mode_local'),
    path('setup/mode/cloud', views.CloudModeSetupView.as_view(), name='fe_setup_mode_cloud'),
    path('setup/display', views.DisplaySetupView.as_view(), name='fe_setup_display'),
    path('dashboard/overview', views.OverviewDashboardView.as_view(), name='fe_dashboard'),
    path('dashboard/device', views.DeviceDashboardView.as_view(), name='fe_dashboard_device'),
    path('dashboard/display', views.DisplayDashboardView.as_view(), name='fe_dashboard_display'),
    path('dashboard/display/image/<int:nr>', views.ImageDisplayDashboardView.as_view(), name='fe_dashboard_display_item'),

    path('status/setup', views.SetupStatusView.as_view(), name='fe_status_setup'),
    path('status/database', views.DatabaseStatusView.as_view(), name='fe_status_database'),
    path('status/display', views.DisplayStatusView.as_view(), name='fe_status_display'),
]

