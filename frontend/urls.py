from django.urls import path, include

from frontend import views

urlpatterns = [
    path('', views.SetupView.as_view(), name='fe_index'),
    path('setup/local', views.LocalSetupView.as_view(), name='fe_setup_local'),
    path('setup/cloud', views.CloudSetupView.as_view(), name='fe_setup_cloud'),
    path('dashboard/overview', views.OverviewDashboardView.as_view(), name='fe_dashboard'),
    path('dashboard/device', views.DeviceDashboardView.as_view(), name='fe_dashboard_device'),

    path('status/database', views.DatabaseStatusView.as_view(), name='fe_status_database'),
    path('status/display', views.DisplayStatusView.as_view(), name='fe_status_display'),
]

