# data/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('', views.data_view, name='data_view'),
    path('import/', views.data_import_view, name='data_import_view'),
]