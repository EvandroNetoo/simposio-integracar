from datetime import timedelta

from accounts.models import User
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from events.forms import EixoTematicoFormSet
from events.models import EixoTematico, Event

from papers.forms import PaperForm
from papers.models import Coauthor, Paper


@override_settings(
    STORAGES={
        'default': {
            'BACKEND': 'django.core.files.storage.FileSystemStorage',
        },
        'staticfiles': {
            'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage',
        },
    }
)
class EixoTematicoTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='author@example.com',
            first_name='Author',
            surname='User',
        )

    def create_event(self, *, name='Evento'):
        now = timezone.now()
        return Event.objects.create(
            owner=self.user,
            name=name,
            edition='1',
            year=2026,
            organizing_institution='Instituição',
            submission_period_start=now,
            submission_period_end=now + timedelta(days=1),
            evaluation_period_start=now + timedelta(days=2),
            evaluation_period_end=now + timedelta(days=3),
            results_publication_date=now + timedelta(days=4),
            contact_email='event@example.com',
        )

    def event_post_data(self, *, eixo_names):
        prefix = EixoTematicoFormSet().prefix
        data = {
            'name': 'Evento com eixos',
            'edition': '1',
            'year': '2026',
            'organizing_institution': 'Instituição',
            'submission_period_start': '2026-06-01T10:00',
            'submission_period_end': '2026-06-02T10:00',
            'evaluation_period_start': '2026-06-03T10:00',
            'evaluation_period_end': '2026-06-04T10:00',
            'results_publication_date': '2026-06-05T10:00',
            'contact_email': 'event@example.com',
            'submission_rules': '',
            f'{prefix}-TOTAL_FORMS': str(len(eixo_names)),
            f'{prefix}-INITIAL_FORMS': '0',
            f'{prefix}-MIN_NUM_FORMS': '1',
            f'{prefix}-MAX_NUM_FORMS': '1000',
        }
        for index, name in enumerate(eixo_names):
            data[f'{prefix}-{index}-name'] = name
        return data

    def test_event_create_requires_at_least_one_eixo_tematico(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse('event_create'),
            self.event_post_data(eixo_names=['']),
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Event.objects.count(), 0)
        self.assertEqual(EixoTematico.objects.count(), 0)

    def test_event_create_saves_multiple_eixos_tematicos(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse('event_create'),
            self.event_post_data(
                eixo_names=['Inteligência Artificial', 'IoT']
            ),
        )

        event = Event.objects.get()
        self.assertRedirects(
            response, reverse('event_detail', args=[event.pk])
        )
        self.assertEqual(
            list(
                event.eixos_tematicos.order_by('name').values_list(
                    'name',
                    flat=True,
                )
            ),
            ['Inteligência Artificial', 'IoT'],
        )

    def test_event_update_edits_event_and_eixos_tematicos(self):
        self.client.force_login(self.user)
        event = self.create_event()
        eixo = EixoTematico.objects.create(event=event, name='Educação')
        prefix = EixoTematicoFormSet().prefix

        response = self.client.post(
            reverse('event_update', args=[event.pk]),
            {
                'name': 'Evento atualizado',
                'edition': '2',
                'year': '2027',
                'organizing_institution': 'Nova instituição',
                'submission_period_start': '2027-06-01T10:00',
                'submission_period_end': '2027-06-02T10:00',
                'evaluation_period_start': '2027-06-03T10:00',
                'evaluation_period_end': '2027-06-04T10:00',
                'results_publication_date': '2027-06-05T10:00',
                'contact_email': 'updated@example.com',
                'submission_rules': 'Novas regras',
                f'{prefix}-TOTAL_FORMS': '2',
                f'{prefix}-INITIAL_FORMS': '1',
                f'{prefix}-MIN_NUM_FORMS': '1',
                f'{prefix}-MAX_NUM_FORMS': '1000',
                f'{prefix}-0-id': eixo.pk,
                f'{prefix}-0-event': event.pk,
                f'{prefix}-0-name': 'Educação atualizada',
                f'{prefix}-1-name': 'Gestão',
            },
        )

        event.refresh_from_db()
        self.assertRedirects(
            response, reverse('event_detail', args=[event.pk])
        )
        self.assertEqual(event.name, 'Evento atualizado')
        self.assertEqual(
            list(
                event.eixos_tematicos.order_by('name').values_list(
                    'name',
                    flat=True,
                )
            ),
            ['Educação atualizada', 'Gestão'],
        )

    def test_paper_form_filters_eixos_by_event(self):
        event = self.create_event()
        other_event = self.create_event(name='Outro evento')
        eixo = EixoTematico.objects.create(event=event, name='Educação')
        other_eixo = EixoTematico.objects.create(
            event=other_event,
            name='Saúde',
        )

        form = PaperForm(event=event)

        self.assertIn(eixo, form.fields['eixo_tematico'].queryset)
        self.assertNotIn(other_eixo, form.fields['eixo_tematico'].queryset)

    def test_paper_form_requires_eixo_tematico(self):
        event = self.create_event()
        EixoTematico.objects.create(event=event, name='Educação')

        form = PaperForm(
            data={
                'title': 'Trabalho',
                'abstract': 'Resumo',
                'eixo_tematico': '',
            },
            event=event,
        )

        self.assertFalse(form.is_valid())
        self.assertIn('eixo_tematico', form.errors)

    def test_paper_form_rejects_eixo_from_another_event(self):
        event = self.create_event()
        other_event = self.create_event(name='Outro evento')
        other_eixo = EixoTematico.objects.create(
            event=other_event,
            name='Saúde',
        )

        form = PaperForm(
            data={
                'title': 'Trabalho',
                'abstract': 'Resumo',
                'eixo_tematico': other_eixo.pk,
            },
            event=event,
        )

        self.assertFalse(form.is_valid())
        self.assertIn('eixo_tematico', form.errors)

    def test_paper_form_edits_with_valid_event_eixo_tematico(self):
        event = self.create_event()
        first_eixo = EixoTematico.objects.create(event=event, name='Educação')
        second_eixo = EixoTematico.objects.create(event=event, name='Gestão')
        paper = Paper.objects.create(
            user=self.user,
            event=event,
            eixo_tematico=first_eixo,
            title='Trabalho',
            abstract='Resumo',
        )

        form = PaperForm(
            data={
                'title': 'Trabalho atualizado',
                'abstract': 'Resumo atualizado',
                'eixo_tematico': second_eixo.pk,
            },
            event=event,
            instance=paper,
        )

        self.assertTrue(form.is_valid())
        updated_paper = form.save()
        self.assertEqual(updated_paper.eixo_tematico, second_eixo)

    def test_paper_update_saves_user_and_manual_coauthors_in_order(self):
        self.client.force_login(self.user)
        event = self.create_event()
        eixo = EixoTematico.objects.create(event=event, name='Educação')
        paper = Paper.objects.create(
            user=self.user,
            event=event,
            eixo_tematico=eixo,
            title='Trabalho',
            abstract='Resumo',
        )
        coauthor_user = User.objects.create_user(
            email='coauthor@example.com',
            first_name='Coauthor',
            surname='User',
        )

        response = self.client.post(
            reverse('paper_change', args=[paper.pk]),
            {
                'title': 'Trabalho atualizado',
                'abstract': 'Resumo atualizado',
                'eixo_tematico': eixo.pk,
                'coauthors-TOTAL_FORMS': '2',
                'coauthors-INITIAL_FORMS': '0',
                'coauthors-MIN_NUM_FORMS': '0',
                'coauthors-MAX_NUM_FORMS': '1000',
                'coauthors-0-user': coauthor_user.pk,
                'coauthors-0-name': '',
                'coauthors-0-email': '',
                'coauthors-0-institution': '',
                'coauthors-0-affiliation_type': '',
                'coauthors-0-authorship_order': '2',
                'coauthors-1-user': '',
                'coauthors-1-name': 'Manual Coauthor',
                'coauthors-1-email': 'manual@example.com',
                'coauthors-1-institution': 'Instituição',
                'coauthors-1-affiliation_type': Coauthor.AffiliationType.OTHER,
                'coauthors-1-authorship_order': '3',
            },
        )

        self.assertRedirects(response, reverse('paper_detail', args=[paper.pk]))
        coauthors = list(paper.coauthors.order_by('authorship_order'))
        self.assertEqual(len(coauthors), 2)
        self.assertEqual(coauthors[0].user, coauthor_user)
        self.assertEqual(coauthors[0].authorship_order, 2)
        self.assertEqual(coauthors[1].email, 'manual@example.com')
        self.assertEqual(coauthors[1].authorship_order, 3)

    def test_paper_detail_shows_pdf_upload_label(self):
        self.client.force_login(self.user)
        event = self.create_event()
        eixo = EixoTematico.objects.create(event=event, name='Educação')
        paper = Paper.objects.create(
            user=self.user,
            event=event,
            eixo_tematico=eixo,
            title='Trabalho',
            abstract='Resumo',
        )

        response = self.client.get(reverse('paper_detail', args=[paper.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Fazer upload do PDF')
