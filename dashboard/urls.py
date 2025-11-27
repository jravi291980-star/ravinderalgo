from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard_view, name='dashboard'),
    # You would add more paths here for manual trade actions (e.g., /manual_square_off)
]