from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User


class RegistrationForm(UserCreationForm):
    email = forms.EmailField(max_length=150)

    class Meta:
        model = User
        fields = ('email', 'username', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        if 'data' in kwargs:
            data = kwargs.pop('data').copy()
            data['username'] = data.get('email')
            kwargs['data'] = data
        super().__init__(*args, **kwargs)
