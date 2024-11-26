# forms.py
from django import forms
from .models import OCLDataImport

class OCLDownloadForm(forms.ModelForm):

    name = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={'class': 'p-2 mt-1 block w-full bg-gray-50 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500'})
    )

    start_date = forms.DateField(
        input_formats=['%Y-%m-%d'],
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'p-2 mt-1 block w-full bg-gray-50 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500'
        })
    )
    end_date = forms.DateField(
        input_formats=['%Y-%m-%d'],
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'p-2 mt-1 block w-full bg-gray-50 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500'
        })
    )

    asset = forms.ChoiceField(
        choices=OCLDataImport.ASSET_CHOICES,
        widget=forms.Select(attrs={'class': 'mt-1 block w-full p-2 bg-gray-50 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500'})
    )

    interval = forms.ChoiceField(
        choices=OCLDataImport.INTERVAL_CHOICES,
        widget=forms.Select(attrs={'class': 'mt-1 block w-full p-2 bg-gray-50 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500'})
    )

    class Meta:
        model = OCLDataImport
        fields = ['name', 'asset', 'interval', 'start_date', 'end_date']

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        if start_date and end_date and start_date > end_date:
            raise forms.ValidationError("Start date must be before end date.")
        return cleaned_data
