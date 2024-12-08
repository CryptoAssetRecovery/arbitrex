# backtesting/urls.py

from django.urls import path
from . import views

app_name = 'backtesting'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('results/<int:backtest_id>/', views.backtest_result, name='backtest_result'),
    path('chart-data/<int:backtest_id>/', views.backtest_chart_data, name='backtest_chart_data'),
    path('status/<int:backtest_id>/', views.backtest_status, name='backtest_status'),
    path('parameters/<int:strategy_id>/', views.strategy_parameters, name='strategy_parameters'),
]