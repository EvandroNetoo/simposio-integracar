from datetime import timedelta
from decimal import Decimal

from accounts.models import User
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from events.models import EixoTematico, Event
from papers.models import Coauthor, Paper, Submission

from reviews.forms import ReviewForm
from reviews.models import (
    CommitteeMember,
    FinalDecision,
    Review,
    ReviewAssignment,
    ReviewCriterion,
    Reviewer,
    ReviewInstrument,
    ReviewRound,
    user_can_decide_event,
    user_can_manage_event,
)

TEST_STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.InMemoryStorage',
    },
    'staticfiles': {
        'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage',
    },
}


@override_settings(STORAGES=TEST_STORAGES)
class ReviewFlowTestCase(TestCase):
    def setUp(self):
        self.now = timezone.now()
        self.owner = self.create_user('owner@example.com')
        self.author = self.create_user('author@example.com')
        self.reviewer_user = self.create_user('reviewer@example.com')
        self.second_reviewer_user = self.create_user('reviewer2@example.com')
        self.outsider = self.create_user('outsider@example.com')
        self.event = Event.objects.create(
            owner=self.owner,
            name='Simpósio',
            edition='1',
            year=2026,
            organizing_institution='Instituição',
            submission_period_start=self.now - timedelta(days=3),
            submission_period_end=self.now + timedelta(days=3),
            evaluation_period_start=self.now - timedelta(days=1),
            evaluation_period_end=self.now + timedelta(days=1),
            results_publication_date=self.now + timedelta(days=2),
            contact_email='event@example.com',
            minimum_reviewers=2,
            blind_review=True,
        )
        self.eixo = EixoTematico.objects.create(
            event=self.event,
            name='Tecnologia',
        )
        self.paper = Paper.objects.create(
            user=self.author,
            event=self.event,
            eixo_tematico=self.eixo,
            title='Trabalho',
            abstract='Resumo',
            status=Paper.Status.SUBMITTED,
        )
        self.submission = Submission.objects.create(
            paper=self.paper,
            file=SimpleUploadedFile(
                'paper.pdf',
                b'%PDF-1.4 test',
                content_type='application/pdf',
            ),
        )
        self.instrument = ReviewInstrument.objects.create(
            event=self.event,
            version=1,
            name='Instrumento',
            created_by=self.owner,
        )
        self.criterion_1 = ReviewCriterion.objects.create(
            instrument=self.instrument,
            name='Mérito',
            weight=Decimal('60'),
            order=1,
        )
        self.criterion_2 = ReviewCriterion.objects.create(
            instrument=self.instrument,
            name='Clareza',
            weight=Decimal('40'),
            order=2,
        )
        self.round = ReviewRound.objects.create(
            paper=self.paper,
            submission=self.submission,
            instrument=self.instrument,
            number=1,
            starts_at=self.now - timedelta(hours=1),
            ends_at=self.now + timedelta(hours=1),
            created_by=self.owner,
        )
        self.reviewer = Reviewer.objects.create(
            event=self.event,
            user=self.reviewer_user,
        )
        self.second_reviewer = Reviewer.objects.create(
            event=self.event,
            user=self.second_reviewer_user,
        )

    def create_user(self, email):
        return User.objects.create_user(
            email=email,
            first_name=email.split('@')[0],
            surname='Teste',
        )

    def create_assignment(self, reviewer=None):
        assignment = ReviewAssignment(
            reviewer=reviewer or self.reviewer,
            round=self.round,
        )
        assignment.full_clean()
        assignment.save()
        return assignment

    def submit_review(self, assignment, score_1='8', score_2='6'):
        review = Review.objects.filter(assignment=assignment).first()
        form = ReviewForm(
            {
                f'criterion_{self.criterion_1.pk}': score_1,
                f'criterion_{self.criterion_2.pk}': score_2,
                'comments_to_author': 'Comentário público',
                'internal_comments': 'Comentário reservado',
                'recommendation': Review.ReviewRecommendation.ACCEPT,
            },
            assignment=assignment,
            instance=review,
        )
        self.assertTrue(form.is_valid(), form.errors)
        return form.save()

    def test_owner_and_committee_roles_have_expected_permissions(self):
        manager = self.create_user('manager@example.com')
        decider = self.create_user('decider@example.com')
        CommitteeMember.objects.create(
            event=self.event,
            user=manager,
            is_manager=True,
        )
        CommitteeMember.objects.create(
            event=self.event,
            user=decider,
            is_decider=True,
        )

        self.assertTrue(user_can_manage_event(self.owner, self.event))
        self.assertTrue(user_can_decide_event(self.owner, self.event))
        self.assertTrue(user_can_manage_event(manager, self.event))
        self.assertFalse(user_can_decide_event(manager, self.event))
        self.assertTrue(user_can_decide_event(decider, self.event))
        self.assertFalse(user_can_manage_event(decider, self.event))

    def test_instrument_used_by_round_is_immutable(self):
        self.instrument.name = 'Alterado'

        with self.assertRaises(ValidationError):
            self.instrument.full_clean()

        self.criterion_1.weight = Decimal('50')
        with self.assertRaises(ValidationError):
            self.criterion_1.full_clean()

    def test_round_requires_weights_totaling_100_and_minimum_reviewers(self):
        self.criterion_2.weight = Decimal('30')
        self.criterion_2.save(update_fields=('weight',))
        self.create_assignment()
        self.create_assignment(self.second_reviewer)

        with self.assertRaises(ValidationError):
            self.round.open()

        self.criterion_2.weight = Decimal('40')
        self.criterion_2.save(update_fields=('weight',))
        self.round.assignments.filter(reviewer=self.second_reviewer).delete()
        with self.assertRaises(ValidationError):
            self.round.open()

    def test_open_round_updates_paper_and_blocks_new_submission(self):
        self.create_assignment()
        self.create_assignment(self.second_reviewer)
        self.round.open()
        self.paper.refresh_from_db()
        self.assertEqual(self.paper.status, Paper.Status.UNDER_REVIEW)

        self.client.force_login(self.author)
        response = self.client.get(
            reverse('submission_create', args=[self.paper.pk])
        )
        self.assertEqual(response.status_code, 409)

    def test_author_and_coauthor_cannot_be_assigned(self):
        author_reviewer = Reviewer.objects.create(
            event=self.event,
            user=self.author,
        )
        with self.assertRaises(ValidationError):
            ReviewAssignment(
                reviewer=author_reviewer,
                round=self.round,
            ).full_clean()

        coauthor_user = self.create_user('coauthor@example.com')
        Coauthor.objects.create(
            paper=self.paper,
            user=coauthor_user,
            authorship_order=2,
        )
        coauthor_reviewer = Reviewer.objects.create(
            event=self.event,
            user=coauthor_user,
        )
        with self.assertRaises(ValidationError):
            ReviewAssignment(
                reviewer=coauthor_reviewer,
                round=self.round,
            ).full_clean()

    def test_review_requires_all_scores_and_calculates_weighted_average(self):
        assignment = self.create_assignment()
        self.round.status = ReviewRound.Status.OPEN
        self.round.save(update_fields=('status',))

        incomplete = ReviewForm(
            {
                f'criterion_{self.criterion_1.pk}': '8',
                'comments_to_author': 'Comentário',
                'recommendation': Review.ReviewRecommendation.ACCEPT,
            },
            assignment=assignment,
        )
        self.assertFalse(incomplete.is_valid())

        review = self.submit_review(assignment)
        self.assertEqual(review.weighted_score, Decimal('7.20'))
        self.assertEqual(review.criterion_scores.count(), 2)

    def test_reviewer_can_edit_published_review_only_inside_deadline(self):
        assignment = self.create_assignment()
        self.round.status = ReviewRound.Status.OPEN
        self.round.save(update_fields=('status',))
        review = self.submit_review(assignment)

        updated = self.submit_review(assignment, score_1='10', score_2='10')
        self.assertEqual(updated.pk, review.pk)
        self.assertEqual(updated.weighted_score, Decimal('10.00'))

        self.round.ends_at = self.now - timedelta(minutes=1)
        self.round.save(update_fields=('ends_at',))
        form = ReviewForm(
            {
                f'criterion_{self.criterion_1.pk}': '9',
                f'criterion_{self.criterion_2.pk}': '9',
                'comments_to_author': 'Tarde',
                'recommendation': Review.ReviewRecommendation.ACCEPT,
            },
            assignment=assignment,
            instance=updated,
        )
        self.assertFalse(form.is_valid())

    def test_double_blind_author_page_hides_reviewer_and_internal_comment(
        self,
    ):
        assignment = self.create_assignment()
        self.round.status = ReviewRound.Status.OPEN
        self.round.save(update_fields=('status',))
        self.submit_review(assignment)

        self.client.force_login(self.author)
        response = self.client.get(
            reverse('paper_detail', args=[self.paper.pk])
        )

        self.assertContains(response, 'Avaliador anônimo')
        self.assertNotContains(response, self.reviewer_user.email)
        self.assertNotContains(response, 'Comentário reservado')
        self.assertContains(response, 'Comentário público')

    def test_protected_download_rejects_outsider_and_allows_assignment(self):
        url = reverse('submission_download', args=[self.submission.pk])
        self.client.force_login(self.outsider)
        self.assertEqual(self.client.get(url).status_code, 403)

        self.create_assignment()
        self.client.force_login(self.reviewer_user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')

    def test_decision_updates_status_and_allows_correction_version(self):
        first = self.create_assignment()
        second = self.create_assignment(self.second_reviewer)
        self.round.status = ReviewRound.Status.OPEN
        self.round.save(update_fields=('status',))
        self.submit_review(first)
        self.submit_review(second, score_1='7', score_2='7')

        decision = FinalDecision.objects.create(
            round=self.round,
            result=FinalDecision.Result.APPROVED_WITH_CHANGES,
            justification='Enviar ajustes.',
            decided_by=self.owner,
        )
        self.paper.refresh_from_db()
        self.round.refresh_from_db()
        self.assertEqual(self.paper.status, Paper.Status.APPROVED_WITH_CHANGES)
        self.assertEqual(self.round.status, ReviewRound.Status.DECIDED)

        correction = Submission.objects.create(
            paper=self.paper,
            file=SimpleUploadedFile(
                'correction.pdf',
                b'%PDF-1.4 corrected',
                content_type='application/pdf',
            ),
        )
        self.assertEqual(correction.version, 2)
        self.assertEqual(decision.round, self.round)

    def test_committee_and_review_views_enforce_roles(self):
        self.client.force_login(self.outsider)
        dashboard = reverse('committee_dashboard', args=[self.event.pk])
        self.assertEqual(self.client.get(dashboard).status_code, 403)

        assignment = self.create_assignment()
        detail = reverse('review_detail', args=[assignment.pk])
        self.assertEqual(self.client.get(detail).status_code, 404)

        self.round.status = ReviewRound.Status.OPEN
        self.round.save(update_fields=('status',))
        self.client.force_login(self.reviewer_user)
        self.assertEqual(self.client.get(detail).status_code, 200)

    def test_owner_can_render_committee_management_pages(self):
        self.client.force_login(self.owner)

        dashboard = self.client.get(
            reverse('committee_dashboard', args=[self.event.pk])
        )
        instrument = self.client.get(
            reverse('review_instrument_create', args=[self.event.pk])
        )
        round_form = self.client.get(
            reverse('review_round_create', args=[self.event.pk])
        )

        self.assertEqual(dashboard.status_code, 200)
        self.assertContains(dashboard, 'Comissão')
        self.assertEqual(instrument.status_code, 200)
        self.assertEqual(round_form.status_code, 200)
