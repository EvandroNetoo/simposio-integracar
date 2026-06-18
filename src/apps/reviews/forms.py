from django import forms
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Exists, OuterRef
from django.utils import timezone
from events.models import EixoTematico

from core.mixins import NoRequiredAttrFormMixin
from reviews.models import (
    CommitteeMember,
    FinalDecision,
    Review,
    ReviewAssignment,
    Reviewer,
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
                    'O dono do evento ja possui os dois papeis.'
                )
            if CommitteeMember.objects.filter(
                event=self.event,
                user=user,
            ).exists():
                raise ValidationError('Este usuario ja integra a comissao.')
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
            raise ValidationError('Este usuario ja e avaliador do evento.')
        return user


class AssignmentForm(NoRequiredAttrFormMixin, forms.Form):
    reviewers = forms.ModelMultipleChoiceField(
        label='Avaliadores',
        queryset=Reviewer.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
    )

    def __init__(self, *args, paper, **kwargs):
        self.paper = paper
        super().__init__(*args, **kwargs)
        self.fields['reviewers'].queryset = (
            Reviewer.objects.filter(event=paper.event)
            .annotate(
                matches_axis=Exists(
                    EixoTematico.objects.filter(
                        pk=paper.eixo_tematico_id,
                        reviewers=OuterRef('pk'),
                    )
                )
            )
            .select_related('user')
            .prefetch_related('eixos_tematicos')
            .order_by('-matches_axis', 'user__first_name', 'user__email')
        )
        self.fields['reviewers'].initial = paper.review_assignments.values_list(
            'reviewer_id',
            flat=True,
        )

    def clean_reviewers(self):
        reviewers = self.cleaned_data['reviewers']
        for reviewer in reviewers:
            assignment = ReviewAssignment(
                reviewer=reviewer,
                paper=self.paper,
            )
            assignment.clean()
        return reviewers

    @transaction.atomic
    def save(self):
        selected = set(
            self.cleaned_data['reviewers'].values_list('id', flat=True)
        )
        self.paper.review_assignments.exclude(
            reviewer_id__in=selected
        ).delete()
        existing = set(
            self.paper.review_assignments.values_list('reviewer_id', flat=True)
        )
        for reviewer_id in selected - existing:
            assignment = ReviewAssignment(
                reviewer_id=reviewer_id,
                paper=self.paper,
            )
            assignment.full_clean()
            assignment.save()
        if selected and self.paper.status not in {
            self.paper.Status.APPROVED,
            self.paper.Status.APPROVED_WITH_CHANGES,
            self.paper.Status.REJECTED,
        }:
            self.paper.status = self.paper.Status.UNDER_REVIEW
            self.paper.save(update_fields=('status',))


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

    def clean(self):
        cleaned_data = super().clean()
        event = self.assignment.paper.event
        now = timezone.now()
        if not event.evaluation_period_start <= now <= event.evaluation_period_end:
            raise ValidationError('O periodo de avaliacao nao esta aberto.')
        return cleaned_data

    @transaction.atomic
    def save(self, commit=True):
        review = super().save(commit=False)
        review.assignment = self.assignment
        review.save()
        self.assignment.completed_at = timezone.now()
        self.assignment.save(update_fields=('completed_at',))
        return review


class FinalDecisionForm(NoRequiredAttrFormMixin, forms.ModelForm):
    class Meta:
        model = FinalDecision
        fields = ('result', 'justification')
        widgets = {'justification': forms.Textarea(attrs={'rows': 5})}

    def __init__(self, *args, paper, **kwargs):
        self.paper = paper
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        if not self.paper.review_assignments.exists():
            raise ValidationError('O trabalho nao possui avaliacoes atribuidas.')
        if self.paper.review_assignments.filter(review__isnull=True).exists():
            raise ValidationError(
                'Todos os avaliadores devem enviar seus pareceres.'
            )
        return cleaned_data
