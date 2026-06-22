from django.db import transaction
from django.http import HttpRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View
from papers.models import Paper
from reviews.models import (
    Reviewer,
    user_can_decide_event,
    user_can_manage_event,
)

from events.forms import EixoTematicoFormSet, EventForm
from events.models import Event


class EventListView(View):
    def get(self, request: HttpRequest):
        events = Event.objects.all()
        return render(request, 'events/event_list.html', {'events': events})


class EventCreateView(View):
    form_class = EventForm
    formset_class = EixoTematicoFormSet
    template_name = 'events/event_create.html'

    def get_context(self, *, form, eixo_formset):
        return {
            'form': form,
            'eixo_formset': eixo_formset,
            'page_title': 'Adicionar Evento',
            'page_subtitle': 'Preencha os dados para criar um novo evento.',
            'submit_label': 'Criar Evento',
        }

    def get(self, request: HttpRequest):
        form = self.form_class()
        eixo_formset = self.formset_class()
        context = self.get_context(form=form, eixo_formset=eixo_formset)
        return render(request, self.template_name, context)

    def post(self, request: HttpRequest):
        form = self.form_class(request.POST)
        event = Event(owner=request.user)
        eixo_formset = self.formset_class(request.POST, instance=event)
        if not (form.is_valid() and eixo_formset.is_valid()):
            context = self.get_context(form=form, eixo_formset=eixo_formset)
            return render(request, self.template_name, context)

        with transaction.atomic():
            event = form.save(commit=False)
            event.owner = request.user
            event.save()
            eixo_formset.instance = event
            eixo_formset.save()

        return redirect('event_detail', pk=event.pk)


class EventUpdateView(EventCreateView):
    def dispatch(self, request, *args, **kwargs):
        self.event = get_object_or_404(
            Event.objects.prefetch_related('eixos_tematicos'),
            pk=kwargs['pk'],
            owner=request.user,
        )
        return super().dispatch(request, *args, **kwargs)

    def get_context(self, *, form, eixo_formset):
        context = super().get_context(form=form, eixo_formset=eixo_formset)
        context.update({
            'event': self.event,
            'page_title': 'Editar Evento',
            'page_subtitle': 'Atualize os dados e eixos temáticos do evento.',
            'submit_label': 'Salvar alterações',
            'back_url': reverse('event_detail', kwargs={'pk': self.event.pk}),
            'back_label': 'Voltar ao evento',
        })
        return context

    def get(self, request: HttpRequest, **kwargs):
        form = self.form_class(instance=self.event)
        eixo_formset = self.formset_class(instance=self.event)
        context = self.get_context(form=form, eixo_formset=eixo_formset)
        return render(request, self.template_name, context)

    def post(self, request: HttpRequest, **kwargs):
        form = self.form_class(request.POST, instance=self.event)
        eixo_formset = self.formset_class(
            request.POST,
            instance=self.event,
        )
        if not (form.is_valid() and eixo_formset.is_valid()):
            context = self.get_context(form=form, eixo_formset=eixo_formset)
            return render(request, self.template_name, context)

        with transaction.atomic():
            event = form.save(commit=False)
            if not event.owner_id:
                event.owner = request.user
            event.save()
            eixo_formset.save()

        return redirect('event_detail', pk=event.pk)


class EventDetailView(View):
    template_name = 'events/event_detail.html'

    def get_management_dashboard(self, event):
        event_papers = list(
            Paper.objects.filter(event=event)
            .select_related('eixo_tematico', 'final_decision')
            .prefetch_related(
                'review_assignments__review',
                'review_assignments__reviewer__user',
            )
            .order_by('title')
        )
        axes = {
            eixo.pk: {
                'name': eixo.name,
                'total': 0,
                'submitted': 0,
                'evaluated': 0,
                'pending': 0,
            }
            for eixo in event.eixos_tematicos.order_by('name')
        }
        status_counts = {status: 0 for status, _label in Paper.Status.choices}
        total_assignments = 0
        completed_assignments = 0
        evaluated_papers = 0
        decided_papers = 0
        pending_papers = 0
        paper_details = []

        for paper in event_papers:
            assignments = list(paper.review_assignments.all())
            assignments_total = len(assignments)
            assignments_completed = sum(
                1 for assignment in assignments if hasattr(assignment, 'review')
            )
            has_decision = hasattr(paper, 'final_decision')
            is_evaluated = (
                assignments_total > 0
                and assignments_completed == assignments_total
            )

            total_assignments += assignments_total
            completed_assignments += assignments_completed
            status_counts[paper.status] = status_counts.get(paper.status, 0) + 1
            if is_evaluated:
                evaluated_papers += 1
            if has_decision:
                decided_papers += 1
            if not has_decision and not is_evaluated:
                pending_papers += 1

            paper_details.append({
                'paper': paper,
                'assignments_total': assignments_total,
                'assignments_completed': assignments_completed,
                'assignments_pending': (
                    assignments_total - assignments_completed
                ),
                'is_evaluated': is_evaluated,
                'has_decision': has_decision,
                'reviewers': [
                    {
                        'name': (
                            assignment.reviewer.user.full_name
                            or assignment.reviewer.user.email
                        ),
                        'completed': hasattr(assignment, 'review'),
                    }
                    for assignment in assignments
                ],
            })

            axis = axes.get(paper.eixo_tematico_id)
            if axis:
                axis['total'] += 1
                if paper.status == Paper.Status.SUBMITTED:
                    axis['submitted'] += 1
                if is_evaluated:
                    axis['evaluated'] += 1
                if not has_decision and not is_evaluated:
                    axis['pending'] += 1

        reviewers = (
            Reviewer.objects.filter(event=event)
            .select_related('user')
            .prefetch_related('assignments__review')
            .order_by('user__first_name', 'user__email')
        )
        reviewer_load = []
        for reviewer in reviewers:
            assignments = list(reviewer.assignments.all())
            assigned = len(assignments)
            completed = sum(
                1 for assignment in assignments if hasattr(assignment, 'review')
            )
            reviewer_load.append({
                'reviewer': reviewer,
                'assigned': assigned,
                'completed': completed,
                'pending': assigned - completed,
            })

        return {
            'total_papers': len(event_papers),
            'submitted_papers': status_counts[Paper.Status.SUBMITTED],
            'under_review_papers': status_counts[Paper.Status.UNDER_REVIEW],
            'evaluated_papers': evaluated_papers,
            'decided_papers': decided_papers,
            'pending_papers': pending_papers,
            'total_assignments': total_assignments,
            'completed_assignments': completed_assignments,
            'pending_assignments': total_assignments - completed_assignments,
            'axes': list(axes.values()),
            'reviewer_load': reviewer_load,
            'papers': paper_details,
        }

    def get(self, request: HttpRequest, pk: int):
        event = get_object_or_404(
            Event.objects.prefetch_related('eixos_tematicos'),
            pk=pk,
        )
        papers = (
            Paper.objects
            .filter(event=event, user=request.user)
            .select_related('event', 'eixo_tematico')
            .prefetch_related('coauthors')
            .order_by('-created_at')
        )
        eixos_tematicos = event.eixos_tematicos.order_by('name')
        can_manage_event = user_can_manage_event(request.user, event)
        can_decide_event = user_can_decide_event(request.user, event)
        context = {
            'event': event,
            'eixos_tematicos': eixos_tematicos,
            'papers': papers,
            'papers_total': papers.count(),
            'can_edit_event': event.owner_id == request.user.id,
            'can_manage_event': can_manage_event,
            'can_decide_event': can_decide_event,
            'can_access_committee': can_manage_event or can_decide_event,
        }
        if context['can_access_committee']:
            context['management_dashboard'] = self.get_management_dashboard(
                event
            )
        return render(request, self.template_name, context)
