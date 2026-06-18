from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import FileResponse, Http404, HttpRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from events.models import Event
from papers.models import Paper, Submission

from reviews.forms import (
    AssignmentForm,
    CommitteeMemberForm,
    FinalDecisionForm,
    ReviewerForm,
    ReviewForm,
)
from reviews.models import (
    ReviewAssignment,
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
            ReviewAssignment.objects.filter(reviewer__user=request.user)
            .select_related(
                'paper__event',
                'paper__eixo_tematico',
            )
            .prefetch_related('paper__submission_set')
            .order_by('paper__event__evaluation_period_end', 'paper__title')
        )
        return render(
            request,
            self.template_name,
            {'assignments': assignments},
        )


class ReviewDetailView(View):
    template_name = 'reviews/review_detail.html'

    def get_assignment(self, request, pk):
        return get_object_or_404(
            ReviewAssignment.objects.select_related(
                'reviewer__user',
                'paper__event',
                'paper__eixo_tematico',
            ),
            pk=pk,
            reviewer__user=request.user,
        )

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
                'paper': assignment.paper,
                'submission': assignment.paper.submission_set.latest(
                    'version'
                ),
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
                'paper': assignment.paper,
                'submission': assignment.paper.submission_set.latest(
                    'version'
                ),
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

        papers = (
            event.papers.prefetch_related(
                'review_assignments__review',
                'review_assignments__reviewer__user',
            )
            .select_related('user', 'eixo_tematico')
            .order_by('title')
        )
        return render(
            request,
            self.template_name,
            {
                'event': event,
                'papers': papers,
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
            messages.success(request, 'Membro da comissao adicionado.')
        else:
            messages.error(request, 'Nao foi possivel adicionar o membro.')
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
            messages.error(request, 'Nao foi possivel adicionar o avaliador.')
        return redirect('committee_dashboard', event_pk=event.pk)


class PaperAssignmentManageView(View):
    template_name = 'reviews/assignment_manage.html'

    def get_paper(self, request, paper_pk):
        paper = get_object_or_404(
            Paper.objects.select_related('event', 'eixo_tematico'),
            pk=paper_pk,
        )
        if not user_can_manage_event(request.user, paper.event):
            raise PermissionDenied
        return paper

    def get(self, request: HttpRequest, paper_pk: int):
        paper = self.get_paper(request, paper_pk)
        return render(
            request,
            self.template_name,
            {
                'paper': paper,
                'form': AssignmentForm(paper=paper),
            },
        )

    def post(self, request: HttpRequest, paper_pk: int):
        paper = self.get_paper(request, paper_pk)
        form = AssignmentForm(request.POST, paper=paper)
        if form.is_valid():
            form.save()
            messages.success(request, 'Distribuicao atualizada.')
            return redirect('paper_assignment_manage', paper_pk=paper.pk)
        return render(
            request,
            self.template_name,
            {'paper': paper, 'form': form},
        )


class FinalDecisionCreateView(View):
    template_name = 'reviews/decision_form.html'

    def get_paper(self, request, paper_pk):
        paper = get_object_or_404(
            Paper.objects.select_related('event').prefetch_related(
                'review_assignments__review',
                'review_assignments__reviewer__user',
            ),
            pk=paper_pk,
        )
        if not user_can_decide_event(request.user, paper.event):
            raise PermissionDenied
        return paper

    def get(self, request: HttpRequest, paper_pk: int):
        paper = self.get_paper(request, paper_pk)
        decision = getattr(paper, 'final_decision', None)
        return render(
            request,
            self.template_name,
            {
                'paper': paper,
                'form': FinalDecisionForm(paper=paper, instance=decision),
            },
        )

    def post(self, request: HttpRequest, paper_pk: int):
        paper = self.get_paper(request, paper_pk)
        decision = getattr(paper, 'final_decision', None)
        form = FinalDecisionForm(request.POST, paper=paper, instance=decision)
        if form.is_valid():
            decision = form.save(commit=False)
            decision.paper = paper
            decision.decided_by = request.user
            decision.save()
            messages.success(request, 'Decisao final publicada.')
            return redirect(
                'committee_dashboard',
                event_pk=paper.event_id,
            )
        return render(
            request,
            self.template_name,
            {'paper': paper, 'form': form},
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
            paper=submission.paper,
            reviewer__user=request.user,
        ).exists()
        if not (is_author or is_committee or is_assigned):
            raise PermissionDenied
        try:
            file_handle = submission.file.open('rb')
        except FileNotFoundError as error:
            raise Http404('Arquivo nao encontrado.') from error
        filename = f'trabalho-{submission.paper_id}-v{submission.version}.pdf'
        return FileResponse(
            file_handle,
            as_attachment=False,
            filename=filename,
            content_type='application/pdf',
        )
