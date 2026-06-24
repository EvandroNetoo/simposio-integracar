from accounts.models import User
from django import forms
from django.core.exceptions import ValidationError
from django.forms import BaseInlineFormSet, inlineformset_factory
from events.models import EixoTematico

from core.mixins import NoRequiredAttrFormMixin
from papers.models import Coauthor, Paper, Submission


class PaperForm(NoRequiredAttrFormMixin, forms.ModelForm):
    class Meta:
        model = Paper
        fields = ['title', 'eixo_tematico', 'abstract']

    def __init__(self, *args, **kwargs):
        self.event = kwargs.pop('event', None)
        super().__init__(*args, **kwargs)

        eixo_field = self.fields['eixo_tematico']
        eixo_field.required = True
        eixo_field.empty_label = 'Selecione um eixo temático'
        eixo_field.queryset = EixoTematico.objects.none()
        if self.event:
            eixo_field.queryset = self.event.eixos_tematicos.order_by('name')

        self.fields['title'].widget.attrs['placeholder'] = 'Título do trabalho'
        self.fields['abstract'].widget.attrs['placeholder'] = (
            'Resumo do trabalho'
        )
        self.fields['abstract'].widget.attrs['rows'] = 2

    def clean_eixo_tematico(self):
        eixo_tematico = self.cleaned_data['eixo_tematico']
        if self.event and eixo_tematico.event_id != self.event.pk:
            raise forms.ValidationError(
                'Selecione um eixo temático do evento escolhido.'
            )
        return eixo_tematico


class CoauthorForm(NoRequiredAttrFormMixin, forms.ModelForm):
    class Meta:
        model = Coauthor
        fields = [
            'user',
            'name',
            'email',
            'institution',
            'affiliation_type',
            'authorship_order',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['user'].queryset = User.objects.order_by('email')
        self.fields['user'].required = False
        self.fields['user'].empty_label = 'Selecione um usuário'

        placeholders = {
            'name': 'Nome do coautor',
            'email': 'Email do coautor',
            'institution': 'Instituição de vínculo',
            'authorship_order': 'Ordem de autoria',
        }
        for field_name, placeholder in placeholders.items():
            self.fields[field_name].widget.attrs['placeholder'] = placeholder


class BaseCoauthorFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        if any(self.errors):
            return

        seen_users = set()
        seen_manual_emails = set()
        for form in self.forms:
            if self.can_delete and self._should_delete_form(form):
                continue

            user = form.cleaned_data.get('user')
            email = form.cleaned_data.get('email', '').strip().lower()

            if user:
                if user.pk in seen_users:
                    raise forms.ValidationError(
                        'Nao adicione o mesmo usuario como coautor mais de uma vez.'
                    )
                seen_users.add(user.pk)
                continue

            if email:
                if email in seen_manual_emails:
                    raise forms.ValidationError(
                        'Nao adicione o mesmo email manual como coautor mais de uma vez.'
                    )
                seen_manual_emails.add(email)


CoauthorFormSet = inlineformset_factory(
    Paper,
    Coauthor,
    form=CoauthorForm,
    formset=BaseCoauthorFormSet,
    extra=0,
    can_delete=True,
)


class SubmissionForm(NoRequiredAttrFormMixin, forms.ModelForm):
    class Meta:
        model = Submission
        fields = ['file', 'observations']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['file'].widget.attrs['accept'] = '.pdf'
        self.fields['observations'].widget.attrs['placeholder'] = (
            'Observações sobre a submissão (opcional)'
        )
        self.fields['observations'].widget.attrs['rows'] = 2

    def clean_file(self):
        file = self.cleaned_data['file']
        if not file.name.lower().endswith('.pdf'):
            raise ValidationError('Envie um arquivo no formato PDF.')
        content_type = getattr(file, 'content_type', '')
        if content_type and content_type != 'application/pdf':
            raise ValidationError('O arquivo enviado não é um PDF válido.')
        return file
