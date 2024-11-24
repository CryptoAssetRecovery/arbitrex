# accounts/views.py

from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login, logout
from django.http import JsonResponse

from .forms import CustomUserCreationForm, AuthenticationForm

from dotenv import load_dotenv
import os

load_dotenv()

def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('email').lower().strip()
            whitelist = os.getenv('EMAIL_WHITELIST', '')
            allowed_emails = [e.lower().strip() for e in whitelist.split(',') if e.strip()]
            
            if email not in allowed_emails:
                messages.error(request, 'You are not authorized to register.')
                return redirect('register')
            
            form.save()
            messages.success(request, f'Account created for {email}! You can now log in.')
            return redirect('login')
    else:
        form = CustomUserCreationForm()
    return render(request, 'accounts/register.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('email')
            password = form.cleaned_data.get('password')
            user = authenticate(email=email, password=password)
            if user is not None:
                auth_login(request, user)
                messages.success(request, f'You are now logged in as {email}.')
                return redirect('dashboard')
            else:
                messages.error(request, 'Invalid email or password.')
        else:
            messages.error(request, 'Invalid email or password.')
    else:
        form = AuthenticationForm()
    return render(request, 'accounts/login.html', {'form': form})

def logout_view(request):
    logout(request)
    messages.success(request, 'You have been logged out.')
    return redirect('login')
