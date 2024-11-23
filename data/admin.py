# data/admin.py

from django.contrib import admin
from .models import BTCPrice

@admin.register(BTCPrice)
class BTCPriceAdmin(admin.ModelAdmin):
    list_display = ('date', 'open', 'high', 'low', 'close', 'volume')
    list_filter = ('date',)
    search_fields = ('date',)