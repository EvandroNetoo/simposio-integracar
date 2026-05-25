from django.db import transaction
from django.http import HttpRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View
from papers.models import Paper

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
        context = {
            'event': event,
            'eixos_tematicos': eixos_tematicos,
            'papers': papers,
            'papers_total': papers.count(),
        }
        return render(request, self.template_name, context)
