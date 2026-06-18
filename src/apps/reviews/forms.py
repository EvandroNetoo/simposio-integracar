from decimal import Decimal

from django import forms
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Exists, Max, OuterRef
from django.forms import inlineformset_factory
from django.utils import timezone
from events.models import EixoTematico
from papers.models import Paper

from core.mixins import NoRequiredAttrFormMixin
from reviews.models import (
    CommitteeMember,
    CriterionScore,
    FinalDecision,
    Review,
    ReviewAssignment,
    ReviewCriterion,
    Reviewer,
    ReviewInstrument,
    ReviewRound,
)


class CommitteeMemberForm(NoRequiredAttrFormMixin, forms.ModelForm):
    class Meta:
        model = CommitteeMember
        fields = ('user', 'is_manager', 'is_decider')

    def __init__(self, *args, event=None, **kwargs):
        self.event = event
        super().__init__(*args, **kwargs)

    def clean_user(self):
        user = self.cleaned_data['user']
        if self.event:
            if self.event.owner_id == user.id:
                raise ValidationError(
                    'O dono do evento já possui os dois papéis.'
                )
            if CommitteeMember.objects.filter(
                event=self.event,
                user=user,
            ).exists():
                raise ValidationError('Este usuário já integra a comissão.')
        return user


class ReviewerForm(NoRequiredAttrFormMixin, forms.ModelForm):
    class Meta:
        model = Reviewer
        fields = ('user', 'eixos_tematicos')

    def __init__(self, *args, event=None, **kwargs):
        self.event = event
        super().__init__(*args, **kwargs)
        if event:
            self.fields[
                'eixos_tematicos'
            ].queryset = event.eixos_tematicos.order_by('name')

    def clean_user(self):
        user = self.cleaned_data['user']
        if (
            self.event
            and Reviewer.objects.filter(
                event=self.event,
                user=user,
            ).exists()
        ):
            raise ValidationError('Este usuário já é avaliador do evento.')
        return user


class ReviewInstrumentForm(NoRequiredAttrFormMixin, forms.ModelForm):
    class Meta:
        model = ReviewInstrument
        fields = ('name',)


class ReviewCriterionForm(NoRequiredAttrFormMixin, forms.ModelForm):
    class Meta:
        model = ReviewCriterion
        fields = ('name', 'description', 'weight', 'order')
        widgets = {
            'description': forms.Textarea(attrs={'rows': 2}),
            'weight': forms.NumberInput(attrs={'min': 0.01, 'max': 100}),
            'order': forms.NumberInput(attrs={'min': 1}),
        }


ReviewCriterionFormSet = inlineformset_factory(
    ReviewInstrument,
    ReviewCriterion,
    form=ReviewCriterionForm,
    extra=0,
    min_num=1,
    validate_min=True,
    can_delete=True,
)


class ReviewRoundForm(NoRequiredAttrFormMixin, forms.ModelForm):
    class Meta:
        model = ReviewRound
        fields = ('paper', 'instrument', 'starts_at', 'ends_at')
        widgets = {
            'starts_at': forms.DateTimeInput(
                attrs={'type': 'datetime-local'},
                format='%Y-%m-%dT%H:%M',
            ),
            'ends_at': forms.DateTimeInput(
                attrs={'type': 'datetime-local'},
                format='%Y-%m-%dT%H:%M',
            ),
        }

    def __init__(self, *args, event, **kwargs):
        self.event = event
        super().__init__(*args, **kwargs)
        self.fields['paper'].queryset = (
            Paper.objects
            .filter(event=event)
            .exclude(submission__isnull=True)
            .distinct()
            .order_by('title')
        )
        self.fields['instrument'].queryset = event.review_instruments.order_by(
            '-version'
        )
        self.fields['starts_at'].initial = event.evaluation_period_start
        self.fields['ends_at'].initial = event.evaluation_period_end

    def clean_paper(self):
        paper = self.cleaned_data['paper']
        latest = paper.submission_set.latest('version')
        if hasattr(latest, 'review_round'):
            raise ValidationError(
                'A versão mais recente já possui uma rodada de avaliação.'
            )
        return paper

    def save(self, commit=True):
        round_ = super().save(commit=False)
        paper = self.cleaned_data['paper']
        round_.submission = paper.submission_set.latest('version')
        last_number = paper.review_rounds.aggregate(last=Max('number'))['last']
        round_.number = (last_number or 0) + 1
        if commit:
            round_.save()
        return round_


class AssignmentForm(NoRequiredAttrFormMixin, forms.Form):
    reviewers = forms.ModelMultipleChoiceField(
        label='Avaliadores',
        queryset=Reviewer.objects.none(),
        widget=forms.CheckboxSelectMultiple,
    )

    def __init__(self, *args, round_, **kwargs):
        self.round = round_
        super().__init__(*args, **kwargs)
        self.fields['reviewers'].queryset = (
            Reviewer.objects
            .filter(event=round_.paper.event)
            .annotate(
                matches_axis=Exists(
                    EixoTematico.objects.filter(
                        pk=round_.paper.eixo_tematico_id,
                        reviewers=OuterRef('pk'),
                    )
                )
            )
            .select_related('user')
            .prefetch_related('eixos_tematicos')
            .order_by('-matches_axis', 'user__first_name', 'user__email')
        )
        self.fields['reviewers'].initial = round_.assignments.values_list(
            'reviewer_id',
            flat=True,
        )

    def clean_reviewers(self):
        reviewers = self.cleaned_data['reviewers']
        for reviewer in reviewers:
            assignment = ReviewAssignment(
                reviewer=reviewer,
                round=self.round,
            )
            assignment.full_clean(exclude=('id',))
        return reviewers

    @transaction.atomic
    def save(self):
        selected = set(
            self.cleaned_data['reviewers'].values_list('id', flat=True)
        )
        self.round.assignments.exclude(reviewer_id__in=selected).delete()
        existing = set(
            self.round.assignments.values_list('reviewer_id', flat=True)
        )
        for reviewer_id in selected - existing:
            assignment = ReviewAssignment(
                reviewer_id=reviewer_id,
                round=self.round,
            )
            assignment.full_clean()
            assignment.save()


class ReviewForm(NoRequiredAttrFormMixin, forms.ModelForm):
    class Meta:
        model = Review
        fields = (
            'comments_to_author',
            'internal_comments',
            'recommendation',
        )
        widgets = {
            'comments_to_author': forms.Textarea(attrs={'rows': 5}),
            'internal_comments': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, assignment, **kwargs):
        self.assignment = assignment
        super().__init__(*args, **kwargs)
        review = self.instance if self.instance.pk else None
        current_scores = {}
        if review:
            current_scores = dict(
                review.criterion_scores.values_list('criterion_id', 'score')
            )
        for criterion in assignment.round.instrument.criteria.all():
            self.fields[f'criterion_{criterion.pk}'] = forms.DecimalField(
                label=criterion.name,
                help_text=criterion.description,
                min_value=Decimal('0'),
                max_value=Decimal('10'),
                decimal_places=2,
                initial=current_scores.get(criterion.pk),
                widget=forms.NumberInput(
                    attrs={'min': 0, 'max': 10, 'step': '0.01'}
                ),
            )

    def clean(self):
        cleaned_data = super().clean()
        if not self.assignment.round.is_editable:
            raise ValidationError('O prazo desta rodada não está aberto.')
        return cleaned_data

    @transaction.atomic
    def save(self, commit=True):
        review = super().save(commit=False)
        review.assignment = self.assignment
        review.weighted_score = Decimal('0')
        review.save()

        for criterion in self.assignment.round.instrument.criteria.all():
            CriterionScore.objects.update_or_create(
                review=review,
                criterion=criterion,
                defaults={
                    'score': self.cleaned_data[f'criterion_{criterion.pk}']
                },
            )
        review.weighted_score = review.calculate_weighted_score()
        review.save(update_fields=('weighted_score', 'updated_at'))
        self.assignment.completed_at = timezone.now()
        self.assignment.save(update_fields=('completed_at',))
        return review


class FinalDecisionForm(NoRequiredAttrFormMixin, forms.ModelForm):
    class Meta:
        model = FinalDecision
        fields = ('result', 'justification')
        widgets = {'justification': forms.Textarea(attrs={'rows': 5})}

    def __init__(self, *args, round_, **kwargs):
        self.round = round_
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        if not self.round.assignments.exists():
            raise ValidationError('A rodada não possui avaliações atribuídas.')
        if self.round.assignments.filter(review__isnull=True).exists():
            raise ValidationError(
                'Todos os avaliadores devem enviar seus pareceres.'
            )
        return cleaned_data
