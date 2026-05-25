from accounts.models import Profile, User
from django.contrib.auth.decorators import user_passes_test
from django.http import HttpResponse
from django.http.request import HttpRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.views import View
from events.models import Event
from reviews.models import Review

from papers.forms import CoauthorFormSet, PaperForm, SubmissionForm
from papers.models import Paper, Submission


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


class PaperListView(View):
    template_name = 'papers/paper_list.html'

    def get(self, request: HttpRequest):
        papers = (
            Paper.objects
            .filter(user=request.user)
            .select_related('event', 'eixo_tematico')
            .prefetch_related('coauthors')
            .order_by('-created_at')
        )
        context = {
            'papers': papers,
            'papers_total': papers.count(),
        }
        return render(request, self.template_name, context)


def user_can_submit_paper(user: User) -> bool:
    try:
        profile = user.profile
    except Profile.DoesNotExist:
        return False

    required_values = [
        user.email,
        user.first_name,
        user.surname,
        profile.cpf,
        profile.phone,
        profile.institution,
        profile.affiliation_type,
        profile.education_level,
        profile.academic_title,
        profile.state,
        profile.city,
        profile.lattes_url,
    ]

    return all(
        value is not None and bool(str(value).strip())
        for value in required_values
    )


@method_decorator(
    user_passes_test(
        user_can_submit_paper,
        reverse_lazy(
            'profile',
            query={'verify_author_fields': 'true'},
        ),
    ),
    name='dispatch',
)
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
        form = self.form_class(event=self.event)
        coauthor_formset = self.build_formset()
        return self.render_form(
            request,
            form=form,
            coauthor_formset=coauthor_formset,
            **self.get_page_context(request),
        )

    def post(self, request: HttpRequest, **kwargs):
        paper = Paper(user=request.user, event=self.event)
        form = self.form_class(
            request.POST,
            event=self.event,
            instance=paper,
        )
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
        return redirect('paper_detail', pk=paper.pk)


class PaperDetailView(View):
    template_name = 'papers/paper_detail.html'

    def get(self, request: HttpRequest, pk: int):
        paper = get_object_or_404(
            Paper.objects.select_related(
                'event',
                'eixo_tematico',
                'user',
            ).prefetch_related('coauthors__user'),
            pk=pk,
            user=request.user,
        )
        coauthors = paper.coauthors.select_related('user').all()
        submissions = list(paper.submission_set.all().order_by('created_at'))
        reviews = list(
            Review.objects
            .filter(assignment__paper=paper)
            .select_related(
                'assignment__reviewer__user',
                'assignment',
            )
            .order_by('submitted_at')
        )
        submission_items = []
        for index, submission in enumerate(submissions):
            next_created_at = None
            if index + 1 < len(submissions):
                next_created_at = submissions[index + 1].created_at
            submission_reviews = [
                review
                for review in reviews
                if review.submitted_at >= submission.created_at
                and (
                    next_created_at is None
                    or review.submitted_at < next_created_at
                )
            ]
            submission_items.append({
                'submission': submission,
                'reviews': submission_reviews,
            })
        context = {
            'paper': paper,
            'event': paper.event,
            'coauthors': coauthors,
            'submission_items': submission_items,
        }
        return render(request, self.template_name, context)


class PaperUpdateView(PaperFormBaseView):
    def dispatch(self, request, *args, **kwargs):
        self.paper = get_object_or_404(
            Paper.objects.select_related('event', 'eixo_tematico', 'user'),
            pk=kwargs['pk'],
            user=request.user,
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
                kwargs={'pk': self.paper.pk},
            ),
            'back_label': 'Voltar ao trabalho',
            'main_author': self.get_main_author(self.paper.user),
            'paper': self.paper,
        }

    def get(self, request: HttpRequest, **kwargs):
        form = self.form_class(event=self.event, instance=self.paper)
        coauthor_formset = self.build_formset(instance=self.paper)
        return self.render_form(
            request,
            form=form,
            coauthor_formset=coauthor_formset,
            **self.get_page_context(),
        )

    def post(self, request: HttpRequest, **kwargs):
        form = self.form_class(
            request.POST,
            event=self.event,
            instance=self.paper,
        )
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
            pk=self.paper.pk,
        )


class SubmissionCreateView(View):
    def get(self, request: HttpRequest, pk: int):
        paper = get_object_or_404(
            Paper,
            pk=pk,
            user=request.user,
        )
        form = SubmissionForm()
        context = {
            'paper': paper,
            'form': form,
        }
        return render(request, 'papers/submission_modal.html', context)

    def post(self, request: HttpRequest, pk: int):
        paper = get_object_or_404(
            Paper,
            pk=pk,
            user=request.user,
        )
        form = SubmissionForm(request.POST, request.FILES)
        if not form.is_valid():
            context = {
                'paper': paper,
                'form': form,
            }
            return render(
                request, 'components/django_form/index.html', context
            )
        submission: Submission = form.save(commit=False)
        submission.paper = paper
        submission.save()
        response = HttpResponse('')
        response.headers['HX-Redirect'] = reverse(
            'paper_detail',
            kwargs={'pk': paper.pk},
        )
        return response
