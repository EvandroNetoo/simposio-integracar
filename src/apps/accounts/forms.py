from django import forms
from django.contrib.auth.forms import (
    AuthenticationForm,
    BaseUserCreationForm,
    PasswordChangeForm,
    PasswordResetForm,
    SetPasswordForm,
)

from accounts.models import Profile, User
from core.mixins import NoRequiredAttrFormMixin

FIELD_CANNOT_BE_EMPTY = (
    'Este campo ja foi preenchido e nao pode ficar em branco.'
)


class SignupForm(NoRequiredAttrFormMixin, BaseUserCreationForm):
    class Meta:
        model = User
        fields = [
            'first_name',
            'surname',
            'email',
        ]

    def clean_email(self):
        email = self.cleaned_data.get('email', '')
        return email.lower()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].widget.attrs['autofocus'] = True

        placeholders = {
            'first_name': 'Digite seu nome',
            'surname': 'Digite seu sobrenome',
            'email': 'Digite seu email',
            'password1': 'Digite sua senha',
            'password2': 'Confirme sua senha',
        }
        for field_name, field in self.fields.items():
            field.widget.attrs['placeholder'] = placeholders.get(
                field_name, ''
            )
            field.required = True


class SigninForm(NoRequiredAttrFormMixin, AuthenticationForm):
    def get_invalid_login_error(self):
        return forms.ValidationError(
            'Credenciais invalidas.',
        )

    def clean_username(self):
        username = self.cleaned_data.get('username', '')
        return username.lower()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['username'].widget.attrs['autofocus'] = False

        placeholders = {
            'username': 'Digite seu email',
            'password': 'Digite sua senha',
        }
        for field_name, field in self.fields.items():
            field.widget.attrs['placeholder'] = placeholders[field_name]


class UserProfileForm(NoRequiredAttrFormMixin, forms.ModelForm):
    email = forms.EmailField(
        label='E-mail',
        disabled=True,
        required=False,
    )

    class Meta:
        model = User
        fields = [
            'first_name',
            'surname',
        ]
        labels = {
            'first_name': 'Nome',
            'surname': 'Sobrenome',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].initial = self.instance.email
        self.fields['email'].widget.attrs['readonly'] = True
        self.fields['first_name'].required = True
        self.fields['surname'].required = True


class ProfileForm(NoRequiredAttrFormMixin, forms.ModelForm):
    required_fields = (
        'cpf',
        'phone',
        'institution',
        'affiliation_type',
        'education_level',
        'academic_title',
        'city',
        'state',
        'lattes_url',
    )

    class Meta:
        model = Profile
        fields = [
            'cpf',
            'phone',
            'institution',
            'affiliation_type',
            'education_level',
            'academic_title',
            'city',
            'state',
            'lattes_url',
        ]
        widgets = {
            'state': forms.TextInput(attrs={'maxlength': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        placeholders = {
            'cpf': 'Digite seu CPF ou documento',
            'phone': 'Digite seu telefone',
            'institution': 'Digite sua instituicao',
            'education_level': 'Ex: Bacharel em Sistemas de Informacao, cursando Tecnico em Meio Ambiente, etc',
            'academic_title': 'Ex: professor, pesquisador, estudante',
            'city': 'Digite sua cidade',
            'state': 'UF',
            'lattes_url': 'https://lattes.cnpq.br/...',
        }

        for field_name, field in self.fields.items():
            field.required = field_name in self.required_fields
            field.widget.attrs['placeholder'] = placeholders.get(
                field_name, ''
            )

        self.fields['cpf'].widget.attrs.update({
            'autocomplete': 'off',
            'data-profile-mask': 'cpf',
            'inputmode': 'numeric',
        })
        self.fields['phone'].widget.attrs.update({
            'autocomplete': 'off',
            'data-profile-mask': 'phone',
            'inputmode': 'tel',
        })
        self.fields['state'].widget.attrs.update({
            'autocomplete': 'off',
            'data-profile-mask': 'state',
            'inputmode': 'text',
            'style': 'text-transform: uppercase;',
        })

    def clean_state(self):
        state = self.cleaned_data.get('state') or ''
        return state.upper()

    def clean(self):
        cleaned_data = super().clean()
        errors = {}

        for field_name in self.fields:
            current_value = getattr(self.instance, field_name, '')
            new_value = cleaned_data.get(field_name)
            if current_value and not new_value:
                errors[field_name] = FIELD_CANNOT_BE_EMPTY

        if errors:
            raise forms.ValidationError(errors)

        return cleaned_data


class CustomPasswordChangeForm(NoRequiredAttrFormMixin, PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        placeholders = {
            'old_password': 'Digite sua senha atual',
            'new_password1': 'Digite sua nova senha',
            'new_password2': 'Confirme sua nova senha',
        }

        for field_name, field in self.fields.items():
            field.widget.attrs['placeholder'] = placeholders.get(
                field_name, ''
            )
            field.widget.attrs['autofocus'] = False


class CustomPasswordResetForm(NoRequiredAttrFormMixin, PasswordResetForm):
    def clean_email(self):
        email = self.cleaned_data.get('email', '')
        return email.lower()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].label = 'E-mail'
        self.fields['email'].widget.attrs.update({
            'placeholder': 'Digite seu email cadastrado',
            'autofocus': True,
        })


class CustomSetPasswordForm(NoRequiredAttrFormMixin, SetPasswordForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        placeholders = {
            'new_password1': 'Digite sua nova senha',
            'new_password2': 'Confirme sua nova senha',
        }

        for field_name, field in self.fields.items():
            field.widget.attrs['placeholder'] = placeholders.get(
                field_name,
                '',
            )