from django.urls import path

from . import views


urlpatterns = [
    path("analytics/", views.analytics_dashboard, name="admin_analytics_dashboard"),
]
