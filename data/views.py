from django.shortcuts import render
from django.views.generic import TemplateView
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import BTCPrice
from .utils import get_historical_data

class DataView(TemplateView):
    template_name = 'data/data.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['btc_prices'] = BTCPrice.objects.all()
        return context
    
class GetDataView(APIView):
    def get(self, request):
        data = get_historical_data()
        return Response(data)