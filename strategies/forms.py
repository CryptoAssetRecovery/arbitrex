# strategies/forms.py

from django import forms
from .models import Strategy
import backtrader as bt

STRATEGY_TEMPLATE = '''
import backtrader as bt

class CustomStrategy(bt.Strategy):
    params = (
        ('param_name', default_value),
    )

    def __init__(self):
        # Initialize indicators
        pass

    def next(self):
        # Define your trading logic
        pass
'''

class StrategyForm(forms.ModelForm):
    class Meta:
        model = Strategy
        fields = ['name', 'description', 'code']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-white text-gray-900',
                'placeholder': 'Enter strategy name'
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-white text-gray-900',
                'rows': 3,
                'placeholder': 'Describe your strategy'
            }),
            'code': forms.Textarea(attrs={
                'class': 'w-full font-mono bg-white text-gray-900',
                'rows': 10,
                'placeholder': 'Enter your strategy code'
            }),
        }

    def __init__(self, *args, **kwargs):
        super(StrategyForm, self).__init__(*args, **kwargs)
        if not self.instance.pk:
            # Autofill with template if creating a new Strategy
            self.fields['code'].initial = STRATEGY_TEMPLATE

    def clean_code(self):
        code = self.cleaned_data.get('code')
        exec_globals = {}
        try:
            exec(code, exec_globals)
        except Exception as e:
            raise forms.ValidationError(f"Error executing code: {e}")

        # Check for Strategy class
        strategy_class = None
        for obj in exec_globals.values():
            if isinstance(obj, type) and issubclass(obj, bt.Strategy):
                strategy_class = obj
                break

        if not strategy_class:
            raise forms.ValidationError("The code must define a class that inherits from backtrader.Strategy.")

        return code