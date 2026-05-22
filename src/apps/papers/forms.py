from accounts.models import User
from django import forms
from django.forms import inlineformset_factory

from core.mixins import NoRequiredAttrFormMixin
from papers.models import Coauthor, Paper, Submission


class PaperForm(NoRequiredAttrFormMixin, forms.ModelForm):
    class Meta:
        model = Paper
        fields = ['title', 'abstract']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['title'].widget.attrs['placeholder'] = 'Título do trabalho'
        self.fields['abstract'].widget.attrs['placeholder'] = (
            'Resumo do trabalho'
        )
        self.fields['abstract'].widget.attrs['rows'] = 2


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


CoauthorFormSet = inlineformset_factory(
    Paper,
    Coauthor,
    form=CoauthorForm,
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
