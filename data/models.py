# data/models.py

from django.db import models

class OCLDataImport(models.Model):
    ASSET_CHOICES = [
        ('BTC', 'Bitcoin'),
        ('ETH', 'Ethereum'),
        ('SOL', 'Solana'),
    ]
    INTERVAL_CHOICES = [
        ('5m', '5 minutes'),
        ('15m', '15 minutes'),
        ('30m', '30 minutes'),
        ('1h', '1 hour'),
        ('4h', '4 hours'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    created_at = models.DateField(auto_now_add=True)
    asset = models.CharField(max_length=3, choices=ASSET_CHOICES)
    interval = models.CharField(max_length=10, choices=INTERVAL_CHOICES)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )

    def __str__(self):
        return f"{self.asset} {self.interval} from {self.start_date} to {self.end_date}"

    class Meta:
        verbose_name = 'OCL Data Import'
        verbose_name_plural = 'OCL Data Imports'
        indexes = [
            models.Index(fields=['created_at']),
            models.Index(fields=['asset', 'interval', 'start_date', 'end_date']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['asset', 'interval', 'start_date', 'end_date'],
                name='unique_data_import'
            )
        ]
    
    def get_price_data(self):
        """Returns price data in a format compatible with the chart view."""
        prices = self.oclprice_set.all().values(
            'date', 'open', 'high', 'low', 'close'
        )
        
        # Rename 'date' to 'Date' to match expected format
        formatted_prices = []
        for price in prices:
            formatted_prices.append({
                'Date': price['date'].strftime("%Y-%m-%d %H:%M:%S"),
                'Open': price['open'],
                'High': price['high'],
                'Low': price['low'],
                'Close': price['close']
            })
        
        return FormattedPriceData(formatted_prices)

class OCLPrice(models.Model):
    date = models.DateTimeField()
    open = models.FloatField()
    high = models.FloatField()
    low = models.FloatField()
    close = models.FloatField()
    volume = models.FloatField()

    data_import = models.ForeignKey(OCLDataImport, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.data_import.asset} on {self.date.strftime('%Y-%m-%d')}"

    class Meta:
        ordering = ['date']
        verbose_name = 'OCL Price'
        verbose_name_plural = 'OCL Prices'
        indexes = [
            models.Index(fields=['date']),
            models.Index(fields=['data_import', 'date']),
        ]

class FormattedPriceData:
    """Helper class to mimic pandas DataFrame interface"""
    def __init__(self, data):
        self.data = data
    
    def to_dict(self, orient='records'):
        if orient == 'records':
            return self.data
        raise ValueError("Only 'records' orientation is supported")