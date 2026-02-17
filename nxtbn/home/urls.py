from django.urls import path

from . import views as home_views


urlpatterns = [
    path('', home_views.home, name='home'),
    path('about/', home_views.about_page, name='about_page'),
    path('contact/', home_views.contact_page, name='contact_page'),
    path('modules/', home_views.modules_index, name='modules_index'),
    path('modules/<slug:app_label>/', home_views.module_detail, name='module_detail'),
]
