from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    # Direct route to the dashboard app
    path('', include('dashboard.urls')),
]