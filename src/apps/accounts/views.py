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

REQUIRED_FIELD_ERROR = 'Este campo e obrigatorio.'
TRUTHY_QUERY_VALUES = {'1', 'true', 'on', 'yes'}


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


class ProfileContextMixin:
    template_name = 'accounts/profile.html'
    profile_form_template = 'accounts/partials/profile_form.html'
    access_form_template = 'accounts/partials/password_form.html'
    user_form_class = UserProfileForm
    profile_form_class = ProfileForm
    password_form_class = CustomPasswordChangeForm
    author_fields_query = 'verify_author_fields'
    next_query = 'next'

    def is_htmx_request(self, request: HttpRequest):
        return request.headers.get('HX-Request') == 'true'

    def redirect_response(self, request: HttpRequest, redirect_url: str):
        if self.is_htmx_request(request):
            return HttpResponseClientRedirect(redirect_url)
        return redirect(redirect_url)

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

    def should_verify_author_fields(self, request: HttpRequest):
        value = request.GET.get(self.author_fields_query, '')
        return value.lower() in TRUTHY_QUERY_VALUES

    def get_profile_query(self, request: HttpRequest, *, keep_prompt=False):
        query = {}
        next_url = self.get_next_url(request)

        if keep_prompt and self.should_verify_author_fields(request):
            query[self.author_fields_query] = 'true'
        if next_url:
            query[self.next_query] = next_url

        return query

    def get_profile_url(self, request: HttpRequest, *, keep_prompt=False):
        query = self.get_profile_query(request, keep_prompt=keep_prompt)
        return reverse('profile', query=query) if query else reverse('profile')

    def get_form_action_url(
        self,
        request: HttpRequest,
        view_name: str,
        *,
        keep_prompt=True,
    ):
        query = self.get_profile_query(request, keep_prompt=keep_prompt)
        return reverse(view_name, query=query) if query else reverse(view_name)

    def iter_required_field_names(self, form):
        for field_name, field in form.fields.items():
            if field.required:
                yield field_name, field

    def get_field_value(self, form, field_name):
        value = form[field_name].value()
        return value.strip() if isinstance(value, str) else value

    def get_incomplete_author_fields(self, user_form, profile_form):
        incomplete_fields = []
        for form in (user_form, profile_form):
            for field_name, field in self.iter_required_field_names(form):
                if not self.get_field_value(form, field_name):
                    incomplete_fields.append(field.label)

        return incomplete_fields

    def get_profile(self, request: HttpRequest):
        profile, _ = Profile.objects.get_or_create(user=request.user)
        return profile

    def prepare_form_for_manual_errors(self, form):
        if not hasattr(form, 'cleaned_data'):
            form.full_clean()
            if not hasattr(form, 'cleaned_data'):
                form.cleaned_data = {}

    def apply_required_field_errors(self, user_form, profile_form):
        for form in (user_form, profile_form):
            self.prepare_form_for_manual_errors(form)
            for field_name, _field in self.iter_required_field_names(form):
                if self.get_field_value(form, field_name):
                    continue

                if not form[field_name].errors:
                    form.add_error(field_name, REQUIRED_FIELD_ERROR)

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
        should_verify_author_fields = self.should_verify_author_fields(request)
        if should_verify_author_fields:
            self.apply_required_field_errors(user_form, profile_form)

        return {
            'user_form': user_form,
            'profile_form': profile_form,
            'password_form': password_form,
            'next_url': next_url,
            'profile_update_url': self.get_form_action_url(
                request,
                'profile_update',
            ),
            'password_update_url': self.get_form_action_url(
                request,
                'profile_password',
            ),
            'verify_author_fields': should_verify_author_fields,
            'incomplete_author_fields': self.get_incomplete_author_fields(
                user_form,
                profile_form,
            ),
        }

    def render_profile_page(self, request: HttpRequest, **context_overrides):
        context = self.get_context(request, **context_overrides)
        return render(request, self.template_name, context)


class ProfileView(ProfileContextMixin, View):
    def get(self, request: HttpRequest):
        return self.render_profile_page(request)


class ProfileUpdateView(ProfileContextMixin, View):
    def post(self, request: HttpRequest):
        profile = self.get_profile(request)
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
            redirect_url = next_url or self.get_profile_url(request)
            return self.redirect_response(request, redirect_url)

        context = self.get_context(
            request,
            user_form=user_form,
            profile_form=profile_form,
        )
        return render(request, self.profile_form_template, context)


class PasswordChangeView(ProfileContextMixin, View):
    def post(self, request: HttpRequest):
        password_form = self.password_form_class(
            request.user,
            request.POST,
        )
        if password_form.is_valid():
            user = password_form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Senha atualizada com sucesso.')
            redirect_url = self.get_profile_url(request, keep_prompt=True)
            return self.redirect_response(request, redirect_url)

        context = self.get_context(
            request,
            password_form=password_form,
        )
        return render(request, self.access_form_template, context)


class SignoutView(View):
    def post(self, request: HttpRequest):
        logout(request)
        return HttpResponseClientRedirect(reverse('signin'))
