# data/models.py

from django.db import models

class BTCPrice(models.Model):
    date = models.DateTimeField(unique=True)
    open = models.FloatField()
    high = models.FloatField()
    low = models.FloatField()
    close = models.FloatField()
    volume = models.FloatField()

    def __str__(self):
        return f"BTC on {self.date.strftime('%Y-%m-%d')}"