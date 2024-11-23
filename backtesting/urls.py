# backtesting/urls.py

from django.urls import path
from . import views

app_name = 'backtesting'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('results/<int:backtest_id>/', views.backtest_result, name='backtest_result'),
]