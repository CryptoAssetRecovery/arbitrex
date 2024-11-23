# strategies/models.py

from django.db import models
from accounts.models import CustomUser

class Strategy(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='strategies')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    code = models.TextField(help_text="Write your Backtrader strategy code here.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name} by {self.user.email}"