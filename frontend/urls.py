from django.urls import path, include

from frontend.views import setup, dashboard, system

urlpatterns = [
    path('', setup.SetupView.as_view(), name='fe_index'),
    path('startup', setup.StartupView.as_view(), name='fe_startup'),
    path('setup/mode/local', setup.LocalModeSetupView.as_view(), name='fe_setup_mode_local'),
    path('setup/mode/cloud', setup.CloudModeSetupView.as_view(), name='fe_setup_mode_cloud'),
    path('setup/display', setup.DisplaySetupView.as_view(), name='fe_setup_display'),
    path('setup/software', setup.SoftwareSetupView.as_view(), name='fe_setup_software'),
    path('dashboard/overview', dashboard.OverviewDashboardView.as_view(), name='fe_dashboard'),
    path('dashboard/device', dashboard.DeviceDashboardView.as_view(), name='fe_dashboard_device'),
    path('dashboard/display', dashboard.DisplayDashboardView.as_view(), name='fe_dashboard_display'),
    path('dashboard/display/image/<int:nr>', dashboard.ImageDisplayDashboardView.as_view(), name='fe_dashboard_display_item'),
    path('dashboard/display/stream', dashboard.StreamDisplayDashboardView.as_view(), name='fe_dashboard_display_stream'),
    path('dashboard/display/stream/<int:nr>', dashboard.ItemStreamDisplayDashboardView.as_view(), name='fe_dashboard_display_stream_item'),
    path('dashboard/software', dashboard.SoftwareDashboardView.as_view(), name='fe_dashboard_software'),
    path('system/help', system.HelpSystemView.as_view(), name='fe_system_help'),
    path('system/usb', system.UsbSystemView.as_view(), name='fe_system_usb'),
    path('system/label', system.LabelSystemView.as_view(), name='fe_system_label'),
]

