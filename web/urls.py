
from django.contrib.auth import views as auth_views
from django.urls import path

from web import views

urlpatterns = [
  path('', views.IndexView.as_view(), name='index'),
  path('register/', views.RegisterView.as_view(), name='register'),
  path('login/', views.LoginView.as_view(), name='login'),
  path('logout/', auth_views.LogoutView.as_view(), name='logout'),
  path('profile/', views.ProfileView.as_view(), name='profile'),
  path('profile/generate-token', views.ProfileGenerateTokenView.as_view(), name='profile_generate_token'),
]


