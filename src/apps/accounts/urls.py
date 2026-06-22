from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from accounts import views
from accounts.forms import CustomPasswordResetForm, CustomSetPasswordForm

urlpatterns = [
    path('cadastrar/', views.SignupView.as_view(), name='signup'),
    path('entrar/', views.SigninView.as_view(), name='signin'),
    path(
        'senha/recuperar/',
        auth_views.PasswordResetView.as_view(
            form_class=CustomPasswordResetForm,
            template_name='accounts/password_reset_form.html',
            email_template_name='accounts/password_reset_email.html',
            subject_template_name='accounts/password_reset_subject.txt',
            success_url=reverse_lazy('password_reset_done'),
        ),
        name='password_reset',
    ),
    path(
        'senha/recuperar/enviado/',
        auth_views.PasswordResetDoneView.as_view(
            template_name='accounts/password_reset_done.html',
        ),
        name='password_reset_done',
    ),
    path(
        'senha/redefinir/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(
            form_class=CustomSetPasswordForm,
            template_name='accounts/password_reset_confirm.html',
            success_url=reverse_lazy('password_reset_complete'),
        ),
        name='password_reset_confirm',
    ),
    path(
        'senha/redefinir/concluido/',
        auth_views.PasswordResetCompleteView.as_view(
            template_name='accounts/password_reset_complete.html',
        ),
        name='password_reset_complete',
    ),
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