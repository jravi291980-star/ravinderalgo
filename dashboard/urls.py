from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard_view, name='dashboard'),
    # New dedicated path to handle the redirect from Dhan's authentication flow
    path('dhan-callback/', views.dhan_callback_view, name='dhan_callback'), 
]