from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_not_required
from django.http import HttpRequest
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View
from django_htmx.http import HttpResponseClientRedirect

from accounts.forms import (
    CustomPasswordChangeForm,
    ProfileForm,
    SigninForm,
    SignupForm,
    UserProfileForm,
)
from accounts.models import Profile


@method_decorator(login_not_required, name='dispatch')
class SignupView(View):
    template_name = 'accounts/signup.html'
    form_class = SignupForm

    def get(self, request: HttpRequest):
        context = {
            'form': self.form_class(),
        }

        return render(request, self.template_name, context)

    def post(self, request: HttpRequest):
        form = self.form_class(request.POST)
        if not form.is_valid():
            context = {
                'form': form,
            }
            return render(
                request, 'components/django_form/index.html', context
            )

        user = form.save()
        login(request, user)

        return HttpResponseClientRedirect(reverse('event_list'))


@method_decorator(login_not_required, name='dispatch')
class SigninView(View):
    template_name = 'accounts/signin.html'
    form_class = SigninForm

    def get(self, request: HttpRequest):
        context = {
            'form': self.form_class(),
        }
        return render(request, self.template_name, context)

    def post(self, request: HttpRequest):
        form = self.form_class(request, request.POST)
        if not form.is_valid():
            context = {
                'form': form,
            }

            return render(
                request, 'components/django_form/index.html', context
            )

        login(request, form.get_user())

        redirect_url = request.GET.get('next', '')
        return HttpResponseClientRedirect(
            redirect_url if redirect_url else reverse('event_list')
        )


class ProfileView(View):
    template_name = 'accounts/profile.html'
    user_form_class = UserProfileForm
    profile_form_class = ProfileForm
    password_form_class = CustomPasswordChangeForm
    author_fields_query = 'verify_author_fields'
    next_query = 'next'

    def get_next_url(self, request: HttpRequest):
        next_url = request.GET.get(self.next_query) or request.POST.get(
            self.next_query,
            '',
        )
        if not next_url:
            return ''

        is_safe_url = url_has_allowed_host_and_scheme(
            next_url,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        )
        return next_url if is_safe_url else ''

    def get_profile_url(self, request: HttpRequest, *, keep_prompt=False):
        query = {}
        next_url = self.get_next_url(request)

        if keep_prompt and request.GET.get(self.author_fields_query):
            query[self.author_fields_query] = request.GET[
                self.author_fields_query
            ]
        if next_url:
            query[self.next_query] = next_url

        return reverse('profile', query=query) if query else reverse('profile')

    def get_incomplete_author_fields(self, user_form, profile_form):
        incomplete_fields = []

        for form in (user_form, profile_form):
            for field_name, field in form.fields.items():
                if not field.required:
                    continue

                value = form[field_name].value()
                if isinstance(value, str):
                    value = value.strip()
                if not value:
                    incomplete_fields.append(field.label)

        return incomplete_fields

    def get_profile(self, request: HttpRequest):
        profile, _ = Profile.objects.get_or_create(user=request.user)
        return profile

    def get_context(
        self,
        request: HttpRequest,
        *,
        user_form=None,
        profile_form=None,
        password_form=None,
    ):
        profile = self.get_profile(request)
        user_form = user_form or self.user_form_class(instance=request.user)
        profile_form = profile_form or self.profile_form_class(
            instance=profile
        )
        password_form = password_form or self.password_form_class(request.user)
        next_url = self.get_next_url(request)
        should_verify_author_fields = (
            request.GET.get(self.author_fields_query) == 'true'
        )

        return {
            'user_form': user_form,
            'profile_form': profile_form,
            'password_form': password_form,
            'next_url': next_url,
            'profile_action_url': self.get_profile_url(
                request,
                keep_prompt=True,
            ),
            'password_action_url': self.get_profile_url(
                request,
                keep_prompt=True,
            ),
            'verify_author_fields': should_verify_author_fields,
            'incomplete_author_fields': self.get_incomplete_author_fields(
                user_form,
                profile_form,
            ),
        }

    def get(self, request: HttpRequest):
        return render(request, self.template_name, self.get_context(request))

    def post(self, request: HttpRequest):
        profile = self.get_profile(request)
        action = request.POST.get('action', 'profile')

        if action == 'password':
            password_form = self.password_form_class(
                request.user,
                request.POST,
            )
            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)
                messages.success(request, 'Senha atualizada com sucesso.')
                return redirect(
                    self.get_profile_url(request, keep_prompt=True)
                )

            context = self.get_context(
                request,
                password_form=password_form,
            )
            return render(request, self.template_name, context)

        user_form = self.user_form_class(
            request.POST,
            instance=request.user,
        )
        profile_form = self.profile_form_class(
            request.POST,
            instance=profile,
        )
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Perfil atualizado com sucesso.')
            next_url = self.get_next_url(request)
            if next_url:
                return redirect(next_url)
            return redirect('profile')

        context = self.get_context(
            request,
            user_form=user_form,
            profile_form=profile_form,
        )
        return render(request, self.template_name, context)


class SignoutView(View):
    def post(self, request: HttpRequest):
        logout(request)
        return HttpResponseClientRedirect(reverse('signin'))
