# data/views.py

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from celery import shared_task
from django.core.paginator import Paginator
from django.db import IntegrityError

from .utils import get_historical_data, parse_row
from .models import OCLPrice, OCLDataImport
from .forms import OCLDownloadForm

@shared_task
def fetch_and_save_ocl_data(data_import_id):
    data_import = OCLDataImport.objects.get(id=data_import_id)
    data_import.status = 'in_progress'
    data_import.save()
    df = get_historical_data(
        timeframe=data_import.interval,
        asset=data_import.asset,
        start_date=data_import.start_date,
        end_date=data_import.end_date
    )
    try:
        for _, row in df.iterrows():
            row_data = parse_row(row)
            OCLPrice.objects.create(**row_data, data_import=data_import)
        
        data_import.start_date = df.iloc[0]['Date']
        data_import.end_date = df.iloc[-1]['Date']
        data_import.status = 'completed'
        data_import.save()
    except IntegrityError:
        data_import.status = 'failed'
        data_import.save()
    
@login_required
def data_view(request):
    # Get all imports
    ocl_data_imports = OCLDataImport.objects.all().order_by('-id')
    
    # Set up pagination
    paginator = Paginator(ocl_data_imports, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'data/data.html', {
        'ocl_data_imports': page_obj,
        'page_obj': page_obj,
        'is_paginated': paginator.num_pages > 1,
        'paginator': paginator,
    })

@login_required
def data_import_view(request):
    if request.method == 'POST':
        form = OCLDownloadForm(request.POST)
        if form.is_valid():
            # print(f"Form is valid: {form.cleaned_data}")
            data_import = form.save()
            fetch_and_save_ocl_data.delay(data_import.id)
            return redirect('data_view')
    else:
        form = OCLDownloadForm()
    return render(request, 'data/data_import.html', {'form': form})