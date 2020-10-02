from django.urls import path

from rest_framework.authtoken import views as auth_views
from api import views

urlpatterns = [
  path('api-token/', auth_views.obtain_auth_token),
  path('rando-numba/', views.RandoNumbaView.as_view()),
]