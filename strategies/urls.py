# strategies/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('', views.StrategyListView.as_view(), name='strategy_list'),
    path('create/', views.StrategyCreateView.as_view(), name='strategy_create'),
    path('<int:pk>/', views.StrategyDetailView.as_view(), name='strategy_detail'),
    path('<int:pk>/update/', views.StrategyUpdateView.as_view(), name='strategy_update'),
    path('<int:pk>/delete/', views.StrategyDeleteView.as_view(), name='strategy_delete'),
    path('chat/', views.chat_with_ai, name='chat_with_ai'),
]