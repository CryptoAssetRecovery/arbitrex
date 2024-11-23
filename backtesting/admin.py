# backtesting/admin.py

from django.contrib import admin
from .models import BacktestResult

@admin.register(BacktestResult)
class BacktestResultAdmin(admin.ModelAdmin):
    list_display = ('id', 'strategy', 'user', 'status', 'created_at', 'completed_at')
    list_filter = ('status', 'strategy', 'user')
    search_fields = ('strategy__name', 'user__username')