from django.urls import path

from accounts import views

urlpatterns = [
    path('cadastrar/', views.SignupView.as_view(), name='signup'),
    path('entrar/', views.SigninView.as_view(), name='signin'),
    path('perfil/', views.ProfileView.as_view(), name='profile'),
    path('sair/', views.SignoutView.as_view(), name='signout'),
]
