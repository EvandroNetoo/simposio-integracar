from decimal import Decimal

from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.http import FileResponse, Http404, HttpRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from events.models import Event
from papers.models import Submission

from reviews.forms import (
    AssignmentForm,
    CommitteeMemberForm,
    FinalDecisionForm,
    ReviewCriterionFormSet,
    ReviewerForm,
    ReviewForm,
    ReviewInstrumentForm,
    ReviewRoundForm,
)
from reviews.models import (
    ReviewAssignment,
    ReviewInstrument,
    ReviewRound,
    user_can_decide_event,
    user_can_manage_event,
)


def get_managed_event(request, pk):
    event = get_object_or_404(Event, pk=pk)
    if not user_can_manage_event(request.user, event):
        raise PermissionDenied
    return event


def get_decidable_event(request, pk):
    event = get_object_or_404(Event, pk=pk)
    if not user_can_decide_event(request.user, event):
        raise PermissionDenied
    return event


class ReviewerDashboardView(View):
    template_name = 'reviews/reviewer_dashboard.html'

    def get(self, request: HttpRequest):
        assignments = (
            ReviewAssignment.objects
            .filter(reviewer__user=request.user)
            .exclude(round__status=ReviewRound.Status.DRAFT)
            .select_related(
                'round__paper__event',
                'round__paper__eixo_tematico',
                'round__submission',
            )
            .prefetch_related('round__instrument__criteria')
            .order_by('round__ends_at')
        )
        return render(
            request,
            self.template_name,
            {'assignments': assignments},
        )


class ReviewDetailView(View):
    template_name = 'reviews/review_detail.html'

    def get_assignment(self, request, pk):
        assignment = get_object_or_404(
            ReviewAssignment.objects.select_related(
                'reviewer__user',
                'round__paper__event',
                'round__paper__eixo_tematico',
                'round__submission',
                'round__instrument',
            ).prefetch_related('round__instrument__criteria'),
            pk=pk,
            reviewer__user=request.user,
        )
        if assignment.round.status == ReviewRound.Status.DRAFT:
            raise Http404
        return assignment

    def get(self, request: HttpRequest, pk: int):
        assignment = self.get_assignment(request, pk)
        review = getattr(assignment, 'review', None)
        form = ReviewForm(
            assignment=assignment,
            instance=review,
        )
        return render(
            request,
            self.template_name,
            {
                'assignment': assignment,
                'paper': assignment.round.paper,
                'form': form,
                'review': review,
            },
        )

    def post(self, request: HttpRequest, pk: int):
        assignment = self.get_assignment(request, pk)
        review = getattr(assignment, 'review', None)
        form = ReviewForm(
            request.POST,
            assignment=assignment,
            instance=review,
        )
        if form.is_valid():
            form.save()
            messages.success(
                request,
                'Parecer salvo e publicado para o autor.',
            )
            return redirect('review_detail', pk=assignment.pk)
        return render(
            request,
            self.template_name,
            {
                'assignment': assignment,
                'paper': assignment.round.paper,
                'form': form,
                'review': review,
            },
        )


class CommitteeDashboardView(View):
    template_name = 'reviews/committee_dashboard.html'

    def get(self, request: HttpRequest, event_pk: int):
        event = get_object_or_404(Event, pk=event_pk)
        can_manage = user_can_manage_event(request.user, event)
        can_decide = user_can_decide_event(request.user, event)
        if not can_manage and not can_decide:
            raise PermissionDenied

        rounds = (
            event.papers
            .prefetch_related(
                'review_rounds__assignments__review',
            )
            .select_related('user', 'eixo_tematico')
            .order_by('title')
        )
        return render(
            request,
            self.template_name,
            {
                'event': event,
                'papers': rounds,
                'instruments': event.review_instruments.prefetch_related(
                    'criteria'
                ),
                'reviewers': event.reviewers.select_related(
                    'user'
                ).prefetch_related('eixos_tematicos'),
                'members': event.committee_members.select_related('user'),
                'can_manage': can_manage,
                'can_decide': can_decide,
                'member_form': CommitteeMemberForm(event=event),
                'reviewer_form': ReviewerForm(event=event),
            },
        )


class CommitteeMemberCreateView(View):
    def post(self, request: HttpRequest, event_pk: int):
        event = get_managed_event(request, event_pk)
        form = CommitteeMemberForm(request.POST, event=event)
        if form.is_valid():
            member = form.save(commit=False)
            member.event = event
            member.full_clean()
            member.save()
            messages.success(request, 'Membro da comissão adicionado.')
        else:
            messages.error(request, 'Não foi possível adicionar o membro.')
        return redirect('committee_dashboard', event_pk=event.pk)


class ReviewerCreateView(View):
    def post(self, request: HttpRequest, event_pk: int):
        event = get_managed_event(request, event_pk)
        form = ReviewerForm(request.POST, event=event)
        if form.is_valid():
            reviewer = form.save(commit=False)
            reviewer.event = event
            reviewer.full_clean()
            reviewer.save()
            form.save_m2m()
            messages.success(request, 'Avaliador adicionado.')
        else:
            messages.error(request, 'Não foi possível adicionar o avaliador.')
        return redirect('committee_dashboard', event_pk=event.pk)


class ReviewInstrumentCreateView(View):
    template_name = 'reviews/instrument_form.html'

    def get_event(self, request, event_pk):
        return get_managed_event(request, event_pk)

    def get(self, request: HttpRequest, event_pk: int):
        event = self.get_event(request, event_pk)
        instrument = ReviewInstrument(event=event, created_by=request.user)
        return render(
            request,
            self.template_name,
            {
                'event': event,
                'form': ReviewInstrumentForm(instance=instrument),
                'formset': ReviewCriterionFormSet(instance=instrument),
            },
        )

    def post(self, request: HttpRequest, event_pk: int):
        event = self.get_event(request, event_pk)
        instrument = ReviewInstrument(event=event, created_by=request.user)
        form = ReviewInstrumentForm(request.POST, instance=instrument)
        formset = ReviewCriterionFormSet(request.POST, instance=instrument)
        if form.is_valid() and formset.is_valid():
            total = sum(
                item.cleaned_data.get('weight', Decimal('0'))
                for item in formset.forms
                if item.cleaned_data and not item.cleaned_data.get('DELETE')
            )
            if total != Decimal('100'):
                formset._non_form_errors = formset.error_class([
                    'Os pesos dos critérios devem totalizar 100%.'
                ])
            else:
                with transaction.atomic():
                    instrument = form.save(commit=False)
                    instrument.event = event
                    instrument.created_by = request.user
                    instrument.version = (
                        event.review_instruments
                        .order_by('-version')
                        .values_list('version', flat=True)
                        .first()
                        or 0
                    ) + 1
                    instrument.save()
                    formset.instance = instrument
                    formset.save()
                messages.success(request, 'Instrumento de avaliação criado.')
                return redirect('committee_dashboard', event_pk=event.pk)
        return render(
            request,
            self.template_name,
            {'event': event, 'form': form, 'formset': formset},
        )


class ReviewRoundCreateView(View):
    template_name = 'reviews/round_form.html'

    def get(self, request: HttpRequest, event_pk: int):
        event = get_managed_event(request, event_pk)
        return render(
            request,
            self.template_name,
            {'event': event, 'form': ReviewRoundForm(event=event)},
        )

    def post(self, request: HttpRequest, event_pk: int):
        event = get_managed_event(request, event_pk)
        form = ReviewRoundForm(request.POST, event=event)
        if form.is_valid():
            round_ = form.save(commit=False)
            round_.created_by = request.user
            round_.full_clean()
            round_.save()
            messages.success(request, 'Rodada criada em rascunho.')
            return redirect('review_round_manage', pk=round_.pk)
        return render(
            request,
            self.template_name,
            {'event': event, 'form': form},
        )


class ReviewRoundManageView(View):
    template_name = 'reviews/round_manage.html'

    def get_round(self, request, pk):
        round_ = get_object_or_404(
            ReviewRound.objects.select_related(
                'paper__event',
                'paper__eixo_tematico',
                'submission',
                'instrument',
            ).prefetch_related(
                'assignments__reviewer__user',
                'instrument__criteria',
            ),
            pk=pk,
        )
        if not user_can_manage_event(request.user, round_.paper.event):
            raise PermissionDenied
        return round_

    def get(self, request: HttpRequest, pk: int):
        round_ = self.get_round(request, pk)
        return render(
            request,
            self.template_name,
            {
                'round': round_,
                'form': AssignmentForm(round_=round_),
            },
        )

    def post(self, request: HttpRequest, pk: int):
        round_ = self.get_round(request, pk)
        if round_.status != ReviewRound.Status.DRAFT:
            raise PermissionDenied
        form = AssignmentForm(request.POST, round_=round_)
        if form.is_valid():
            form.save()
            messages.success(request, 'Distribuição atualizada.')
            return redirect('review_round_manage', pk=round_.pk)
        return render(
            request,
            self.template_name,
            {'round': round_, 'form': form},
        )


class ReviewRoundOpenView(View):
    def post(self, request: HttpRequest, pk: int):
        round_ = get_object_or_404(
            ReviewRound.objects.select_related(
                'paper__event',
                'submission',
                'instrument',
            ),
            pk=pk,
        )
        if not user_can_manage_event(request.user, round_.paper.event):
            raise PermissionDenied
        try:
            round_.open()
        except ValidationError as error:
            messages.error(request, ' '.join(error.messages))
        else:
            messages.success(request, 'Rodada aberta para avaliação.')
        return redirect('review_round_manage', pk=round_.pk)


class ReviewRoundCloseView(View):
    def post(self, request: HttpRequest, pk: int):
        round_ = get_object_or_404(
            ReviewRound.objects.select_related('paper__event'),
            pk=pk,
        )
        if not user_can_manage_event(request.user, round_.paper.event):
            raise PermissionDenied
        try:
            round_.close()
        except ValidationError as error:
            messages.error(request, ' '.join(error.messages))
        else:
            messages.success(request, 'Rodada encerrada.')
        return redirect('review_round_manage', pk=round_.pk)


class FinalDecisionCreateView(View):
    template_name = 'reviews/decision_form.html'

    def get_round(self, request, pk):
        round_ = get_object_or_404(
            ReviewRound.objects.select_related(
                'paper__event'
            ).prefetch_related('assignments__review'),
            pk=pk,
        )
        if not user_can_decide_event(request.user, round_.paper.event):
            raise PermissionDenied
        return round_

    def get(self, request: HttpRequest, pk: int):
        round_ = self.get_round(request, pk)
        return render(
            request,
            self.template_name,
            {'round': round_, 'form': FinalDecisionForm(round_=round_)},
        )

    def post(self, request: HttpRequest, pk: int):
        round_ = self.get_round(request, pk)
        form = FinalDecisionForm(request.POST, round_=round_)
        if form.is_valid():
            decision = form.save(commit=False)
            decision.round = round_
            decision.decided_by = request.user
            decision.save()
            messages.success(request, 'Decisão final publicada.')
            return redirect(
                'committee_dashboard',
                event_pk=round_.paper.event_id,
            )
        return render(
            request,
            self.template_name,
            {'round': round_, 'form': form},
        )


class SubmissionDownloadView(View):
    def get(self, request: HttpRequest, pk: int):
        submission = get_object_or_404(
            Submission.objects.select_related('paper__event', 'paper__user'),
            pk=pk,
        )
        event = submission.paper.event
        is_author = submission.paper.user_id == request.user.id
        is_committee = user_can_manage_event(
            request.user, event
        ) or user_can_decide_event(request.user, event)
        is_assigned = ReviewAssignment.objects.filter(
            round__submission=submission,
            reviewer__user=request.user,
        ).exists()
        if not (is_author or is_committee or is_assigned):
            raise PermissionDenied
        try:
            file_handle = submission.file.open('rb')
        except FileNotFoundError as error:
            raise Http404('Arquivo não encontrado.') from error
        filename = f'trabalho-{submission.paper_id}-v{submission.version}.pdf'
        return FileResponse(
            file_handle,
            as_attachment=False,
            filename=filename,
            content_type='application/pdf',
        )
