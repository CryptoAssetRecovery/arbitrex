# data/admin.py

from django.contrib import admin
from .models import OCLDataImport, OCLPrice

@admin.register(OCLDataImport)
class OCLDataImportAdmin(admin.ModelAdmin):
    list_display = ('asset', 'interval', 'start_date', 'end_date')
    list_filter = ('asset', 'interval', 'start_date', 'end_date')
    search_fields = ('date',)

@admin.register(OCLPrice)
class OCLPriceAdmin(admin.ModelAdmin):
    list_display = ('get_asset', 'get_interval', 'date', 'open', 'close', 'volume')
    list_filter = ('data_import__asset', 'data_import__interval', 'date')
    search_fields = ('date',)

    def get_asset(self, obj):
        return obj.data_import.asset
    get_asset.short_description = 'Asset'

    def get_interval(self, obj):
        return obj.data_import.interval
    get_interval.short_description = 'Interval'