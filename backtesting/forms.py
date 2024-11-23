# backtesting/forms.py

from django import forms
from strategies.models import Strategy

class BacktestForm(forms.Form):
    strategy = forms.ModelChoiceField(
        queryset=Strategy.objects.all(),
        widget=forms.Select(attrs={
            'class': 'mt-1 block w-full bg-gray-50 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500'
        })
    )
    parameters = forms.JSONField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'mt-1 block w-full bg-gray-50 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500',
            'rows': 4,
            'placeholder': '{"key": "value"}'
        })
    )