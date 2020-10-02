import logging

from django.contrib.auth.mixins import LoginRequiredMixin

from django.contrib.auth import login, authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError
from django.shortcuts import render, redirect, reverse, get_object_or_404

from django.views import View

from rest_framework.authtoken.models import Token

from web.forms import RegistrationForm


logger = logging.getLogger()

class RegisterView(View):
    def get(self, request):
        return render(request, 'web/register.html', {'form': RegistrationForm()})
    
    def post(self, request):
        form = RegistrationForm(data=request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect(reverse('index'))
        return render(request, 'web/register.html', {'form': form})


class LoginView(View):
    def get(self, request):
        return render(request, 'web/login.html', {'form': AuthenticationForm()})
    
    def post(self, request):
        '''Low level auth using AuthenticationForm.clean'''
        form = AuthenticationForm(request, data=request.POST)
        user = None
        if form.is_valid():
            try:
                form.clean()
                user = form.get_user()
            except ValidationError as e:
                logger.warn('Invalid creds', e)

        if user:
            login(request, user)
            return redirect(reverse('index'))

        return render(request, 'web/login.html', {'invalid_creds': True})


class IndexView(LoginRequiredMixin, View):
    def get(self, request):
        return render(request, 'web/index.html')


class ProfileView(LoginRequiredMixin, View):
    def get(self, request):
        token, _ = Token.objects.get_or_create(user=request.user)
        return render(request, 'web/profile.html', { 'token': token })


class ProfileGenerateTokenView(LoginRequiredMixin, View):
    def post(self, request):
        Token.objects.get(user=request.user).delete()
        return redirect(reverse('profile'))

