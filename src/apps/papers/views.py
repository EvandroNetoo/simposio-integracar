from django.http.request import HttpRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View
from events.models import Event

from papers.forms import CoauthorFormSet, PaperForm
from papers.models import Paper


class PaperFormBaseView(View):
    form_class = PaperForm
    template_name = 'papers/paper_form.html'
    formset_prefix = 'coauthors'

    def get_main_author(self, user):
        return user.full_name or user.email

    def build_formset(self, data=None, *, instance=None):
        return CoauthorFormSet(
            data,
            instance=instance,
            prefix=self.formset_prefix,
        )

    def build_form_context(self, *, form, coauthor_formset, **extra):
        context = {
            'form': form,
            'coauthor_formset': coauthor_formset,
            'event': self.event,
        }
        context.update(extra)
        return context

    def render_form(self, request, *, form, coauthor_formset, **extra):
        context = self.build_form_context(
            form=form,
            coauthor_formset=coauthor_formset,
            **extra,
        )
        return render(request, self.template_name, context)


class PaperCreateView(PaperFormBaseView):
    def dispatch(self, request, *args, **kwargs):
        self.event = get_object_or_404(Event, pk=kwargs['event_pk'])
        return super().dispatch(request, *args, **kwargs)

    def get_page_context(self, request):
        return {
            'page_title': 'Enviar trabalho',
            'page_subtitle': 'Preencha os dados para cadastrar um novo trabalho.',
            'submit_label': 'Enviar trabalho',
            'back_url': reverse('event_detail', kwargs={'pk': self.event.pk}),
            'back_label': 'Voltar ao evento',
            'main_author': self.get_main_author(request.user),
        }

    def get(self, request: HttpRequest, **kwargs):
        form = self.form_class()
        coauthor_formset = self.build_formset()
        return self.render_form(
            request,
            form=form,
            coauthor_formset=coauthor_formset,
            **self.get_page_context(request),
        )

    def post(self, request: HttpRequest, **kwargs):
        paper = Paper(user=request.user, event=self.event)
        form = self.form_class(request.POST, instance=paper)
        coauthor_formset = self.build_formset(
            request.POST,
            instance=paper,
        )
        if not (form.is_valid() and coauthor_formset.is_valid()):
            return self.render_form(
                request,
                form=form,
                coauthor_formset=coauthor_formset,
                **self.get_page_context(request),
            )
        paper = form.save(commit=False)
        paper.user = request.user
        paper.event = self.event
        paper.save()
        coauthor_formset.instance = paper
        coauthor_formset.save()
        return redirect('paper_detail', event_pk=paper.event_id, pk=paper.pk)


class PaperDetailView(View):
    template_name = 'papers/paper_detail.html'

    def get(self, request: HttpRequest, event_pk: int, pk: int):
        paper = get_object_or_404(
            Paper.objects.select_related('event', 'user').prefetch_related(
                'coauthors__user'
            ),
            pk=pk,
            event_id=event_pk,
        )
        coauthors = paper.coauthors.select_related('user').all()
        context = {
            'paper': paper,
            'event': paper.event,
            'coauthors': coauthors,
        }
        return render(request, self.template_name, context)


class PaperUpdateView(PaperFormBaseView):
    def dispatch(self, request, *args, **kwargs):
        self.paper = get_object_or_404(
            Paper.objects.select_related('event', 'user'),
            pk=kwargs['pk'],
            event_id=kwargs['event_pk'],
        )
        self.event = self.paper.event
        return super().dispatch(request, *args, **kwargs)

    def get_page_context(self):
        return {
            'page_title': 'Editar trabalho',
            'page_subtitle': 'Atualize as informações do trabalho.',
            'submit_label': 'Salvar alterações',
            'back_url': reverse(
                'paper_detail',
                kwargs={'event_pk': self.event.pk, 'pk': self.paper.pk},
            ),
            'back_label': 'Voltar ao trabalho',
            'main_author': self.get_main_author(self.paper.user),
            'paper': self.paper,
        }

    def get(self, request: HttpRequest, **kwargs):
        form = self.form_class(instance=self.paper)
        coauthor_formset = self.build_formset(instance=self.paper)
        return self.render_form(
            request,
            form=form,
            coauthor_formset=coauthor_formset,
            **self.get_page_context(),
        )

    def post(self, request: HttpRequest, **kwargs):
        form = self.form_class(request.POST, instance=self.paper)
        coauthor_formset = self.build_formset(
            request.POST,
            instance=self.paper,
        )
        if not (form.is_valid() and coauthor_formset.is_valid()):
            return self.render_form(
                request,
                form=form,
                coauthor_formset=coauthor_formset,
                **self.get_page_context(),
            )

        form.save()
        coauthor_formset.save()
        return redirect(
            'paper_detail',
            event_pk=self.event.pk,
            pk=self.paper.pk,
        )


