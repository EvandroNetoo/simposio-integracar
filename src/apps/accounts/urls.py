from django.urls import path

from accounts import views

urlpatterns = [
    path('cadastrar/', views.SignupView.as_view(), name='signup'),
    path('entrar/', views.SigninView.as_view(), name='signin'),
    path('perfil/', views.ProfileView.as_view(), name='profile'),
    path(
        'perfil/atualizar/',
        views.ProfileUpdateView.as_view(),
        name='profile_update',
    ),
    path(
        'perfil/senha/',
        views.PasswordChangeView.as_view(),
        name='profile_password',
    ),
    path('sair/', views.SignoutView.as_view(), name='signout'),
]
