# backtesting/forms.py

from django import forms
from strategies.models import Strategy
import json

class BacktestForm(forms.Form):
    TIMEFRAME_CHOICES = [
        ('5m', '5 Minutes'),
        ('15m', '15 Minutes'),
        ('30m', '30 Minutes'),
        ('1h', '1 Hour'),
        ('4h', '4 Hours'),
        ('1d', '1 Day'),
    ]
    
    strategy = forms.ModelChoiceField(
        queryset=Strategy.objects.all().order_by('-created_at'),
        widget=forms.Select(attrs={
            'class': 'mt-1 block w-full p-2 bg-gray-50 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500'
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
    timeframe = forms.ChoiceField(
        choices=TIMEFRAME_CHOICES,
        widget=forms.Select(attrs={
            'class': 'mt-1 block w-full bg-gray-50 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500'
        }),
        initial='4h'
    )
    
    # Earliest date available is 2019-09-23
    start_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'min': '2019-09-23',
            'class': 'p-2 mt-1 block w-full bg-gray-50 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500'
        })
    )

    end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'p-2 mt-1 block w-full bg-gray-50 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500'
        })
    )

    commission = forms.FloatField(
        required=False,
        initial=0.1,
        widget=forms.NumberInput(attrs={'class': 'p-2 mt-1 block w-full bg-gray-50 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500'})
    )

    slippage = forms.FloatField(
        required=False,
        initial=0.01,
        widget=forms.NumberInput(attrs={'class': 'p-2 mt-1 block w-full bg-gray-50 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500'})
    )

    leverage = forms.IntegerField(
        required=False,
        initial=1,
        widget=forms.NumberInput(attrs={'class': 'p-2 mt-1 block w-full bg-gray-50 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500'})
    )

    def clean_parameters(self):
        data = self.cleaned_data.get('parameters')
        if data is None:
            return {}
        if isinstance(data, str):
            try:
                return json.loads(data)
            except json.JSONDecodeError:
                raise forms.ValidationError("Invalid JSON format.")
        return data