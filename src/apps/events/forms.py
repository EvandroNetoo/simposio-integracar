from django import forms

from core.mixins import NoRequiredAttrFormMixin
from events.models import Event


class EventForm(forms.ModelForm, NoRequiredAttrFormMixin):
    class Meta:
        model = Event
        fields = [
            'name',
            'edition',
            'year',
            'organizing_institution',
            'submission_period_start',
            'submission_period_end',
            'evaluation_period_start',
            'evaluation_period_end',
            'results_publication_date',
            'contact_email',
            'submission_rules',
            'blind_review',
        ]
        widgets = {
            'submission_period_start': forms.DateInput(
                attrs={'type': 'datetime-local'}
            ),
            'submission_period_end': forms.DateInput(
                attrs={'type': 'datetime-local'}
            ),
            'evaluation_period_start': forms.DateInput(
                attrs={'type': 'datetime-local'}
            ),
            'evaluation_period_end': forms.DateInput(
                attrs={'type': 'datetime-local'}
            ),
            'results_publication_date': forms.DateInput(
                attrs={'type': 'datetime-local'}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        placeholders = {
            'name': 'Digite o nome do evento',
            'edition': 'Digite a edição do evento (ex: "1ª", "2ª", etc.)',
            'year': 'Digite o ano do evento',
            'organizing_institution': 'Digite a instituição organizadora do evento',
            'contact_email': 'Digite o e-mail de contato da organização',
            'submission_rules': 'Digite as regras gerais de submissão para o evento',
        }
        for field_name, placeholder in placeholders.items():
            self.fields[field_name].widget.attrs['placeholder'] = placeholder

        self.fields['submission_rules'].widget.attrs['rows'] = 1

        self.fields['edition'].widget.attrs.update({'inputmode': 'numeric'})
