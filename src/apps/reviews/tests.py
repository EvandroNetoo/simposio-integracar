from datetime import timedelta

from accounts.models import User
from django.core import mail
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from events.models import EixoTematico, Event
from papers.models import Coauthor, Paper, Submission

from reviews.forms import AssignmentForm, ReviewForm
from reviews.models import (
    CommitteeMember,
    FinalDecision,
    Review,
    ReviewAssignment,
    Reviewer,
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
@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class ReviewFlowTestCase(TestCase):
    def setUp(self):
        mail.outbox = []
        self.now = timezone.now()
        self.owner = self.create_user('owner@example.com')
        self.author = self.create_user('author@example.com')
        self.reviewer_user = self.create_user('reviewer@example.com')
        self.second_reviewer_user = self.create_user('reviewer2@example.com')
        self.outsider = self.create_user('outsider@example.com')
        self.event = Event.objects.create(
            owner=self.owner,
            name='Simposio',
            edition='1',
            year=2026,
            organizing_institution='Instituicao',
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
            paper=self.paper,
        )
        assignment.full_clean()
        assignment.save()
        return assignment

    def submit_review(self, assignment):
        review = Review.objects.filter(assignment=assignment).first()
        form = ReviewForm(
            {
                'comments_to_author': 'Comentario publico',
                'internal_comments': 'Comentario reservado',
                'recommendation': Review.ReviewRecommendation.APPROVE,
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

    def test_committee_assigns_reviewers_directly_to_paper(self):
        form = AssignmentForm(
            {'reviewers': [self.reviewer.pk, self.second_reviewer.pk]},
            paper=self.paper,
        )
        self.assertTrue(form.is_valid(), form.errors)
        form.save()

        self.paper.refresh_from_db()
        self.assertEqual(self.paper.review_assignments.count(), 2)
        self.assertEqual(self.paper.status, Paper.Status.UNDER_REVIEW)

        form = AssignmentForm({'reviewers': [self.reviewer.pk]}, paper=self.paper)
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        self.assertEqual(self.paper.review_assignments.count(), 1)

    def test_author_and_coauthor_cannot_be_assigned(self):
        author_reviewer = Reviewer.objects.create(
            event=self.event,
            user=self.author,
        )
        with self.assertRaises(ValidationError):
            ReviewAssignment(
                reviewer=author_reviewer,
                paper=self.paper,
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
                paper=self.paper,
            ).full_clean()

    def test_reviewer_submits_simple_review_without_grades(self):
        assignment = self.create_assignment()

        review = self.submit_review(assignment)
        self.assertEqual(
            review.recommendation,
            Review.ReviewRecommendation.APPROVE,
        )
        self.assertEqual(review.comments_to_author, 'Comentario publico')

        assignment.refresh_from_db()
        self.assertIsNotNone(assignment.completed_at)

    def test_reviewer_review_notifies_authors_by_email(self):
        assignment = self.create_assignment()

        self.client.force_login(self.reviewer_user)
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                reverse('review_detail', args=[assignment.pk]),
                {
                    'comments_to_author': 'Comentario publico',
                    'internal_comments': 'Comentario reservado',
                    'recommendation': Review.ReviewRecommendation.APPROVE,
                },
            )

        self.assertRedirects(
            response,
            reverse('review_detail', args=[assignment.pk]),
        )
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.author.email])
        self.assertIn('Comentario publico', mail.outbox[0].body)

    def test_reviewer_can_edit_published_review_inside_event_deadline(self):
        assignment = self.create_assignment()
        review = self.submit_review(assignment)

        form = ReviewForm(
            {
                'comments_to_author': 'Atualizado',
                'internal_comments': 'Comentario reservado',
                'recommendation': Review.ReviewRecommendation.REJECT,
            },
            assignment=assignment,
            instance=review,
        )
        self.assertTrue(form.is_valid(), form.errors)
        updated = form.save()
        self.assertEqual(updated.pk, review.pk)
        self.assertEqual(
            updated.recommendation,
            Review.ReviewRecommendation.REJECT,
        )

        self.event.evaluation_period_end = self.now - timedelta(minutes=1)
        self.event.save(update_fields=('evaluation_period_end',))
        form = ReviewForm(
            {
                'comments_to_author': 'Tarde',
                'recommendation': Review.ReviewRecommendation.APPROVE,
            },
            assignment=assignment,
            instance=updated,
        )
        self.assertFalse(form.is_valid())

    def test_double_blind_author_page_hides_reviewer_and_internal_comment(self):
        assignment = self.create_assignment()
        self.submit_review(assignment)

        self.client.force_login(self.author)
        response = self.client.get(
            reverse('paper_detail', args=[self.paper.pk])
        )

        self.assertContains(response, 'Avaliador anonimo')
        self.assertNotContains(response, self.reviewer_user.email)
        self.assertNotContains(response, 'Comentario reservado')
        self.assertContains(response, 'Comentario publico')

    def test_linked_coauthor_can_access_paper_reviews_in_system(self):
        coauthor_user = self.create_user('linked-coauthor@example.com')
        Coauthor.objects.create(
            paper=self.paper,
            user=coauthor_user,
            authorship_order=2,
        )
        assignment = self.create_assignment()
        self.submit_review(assignment)

        self.client.force_login(coauthor_user)
        detail = self.client.get(reverse('paper_detail', args=[self.paper.pk]))
        paper_list = self.client.get(reverse('paper_list'))

        self.assertEqual(detail.status_code, 200)
        self.assertContains(detail, 'Comentario publico')
        self.assertContains(paper_list, self.paper.title)

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
        self.submit_review(first)
        self.submit_review(second)

        decision = FinalDecision.objects.create(
            paper=self.paper,
            result=FinalDecision.Result.APPROVED_WITH_CHANGES,
            justification='Enviar ajustes.',
            decided_by=self.owner,
        )
        self.paper.refresh_from_db()
        self.assertEqual(self.paper.status, Paper.Status.APPROVED_WITH_CHANGES)

        correction = Submission.objects.create(
            paper=self.paper,
            file=SimpleUploadedFile(
                'correction.pdf',
                b'%PDF-1.4 corrected',
                content_type='application/pdf',
            ),
        )
        self.assertEqual(correction.version, 2)
        self.assertEqual(decision.paper, self.paper)

    def test_final_decision_notifies_authors_by_email(self):
        first = self.create_assignment()
        second = self.create_assignment(self.second_reviewer)
        self.submit_review(first)
        self.submit_review(second)

        self.client.force_login(self.owner)
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                reverse('final_decision_create', args=[self.paper.pk]),
                {
                    'result': FinalDecision.Result.APPROVED,
                    'justification': 'Parabens.',
                },
            )

        self.assertRedirects(
            response,
            reverse('committee_dashboard', args=[self.event.pk]),
        )
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.author.email])
        self.assertIn('Parabens.', mail.outbox[0].body)

    def test_new_assignment_notifies_reviewer_by_email(self):
        self.client.force_login(self.owner)

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                reverse('paper_assignment_manage', args=[self.paper.pk]),
                {'reviewers': [self.reviewer.pk]},
            )

        self.assertRedirects(
            response,
            reverse('paper_assignment_manage', args=[self.paper.pk]),
        )
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.reviewer_user.email])
        self.assertIn(self.paper.title, mail.outbox[0].body)

    def test_new_submission_notifies_event_committee_by_email(self):
        self.client.force_login(self.author)

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                reverse('submission_create', args=[self.paper.pk]),
                {
                    'file': SimpleUploadedFile(
                        'paper-v2.pdf',
                        b'%PDF-1.4 second',
                        content_type='application/pdf',
                    ),
                    'observations': 'Nova versao.',
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(
            set(mail.outbox[0].to),
            {self.owner.email, self.event.contact_email},
        )
        self.assertIn(self.paper.title, mail.outbox[0].body)

    def test_committee_and_review_views_enforce_roles(self):
        self.client.force_login(self.outsider)
        dashboard = reverse('committee_dashboard', args=[self.event.pk])
        self.assertEqual(self.client.get(dashboard).status_code, 403)

        assignment = self.create_assignment()
        detail = reverse('review_detail', args=[assignment.pk])
        self.assertEqual(self.client.get(detail).status_code, 404)

        self.client.force_login(self.reviewer_user)
        self.assertEqual(self.client.get(detail).status_code, 200)

    def test_owner_can_render_committee_management_pages(self):
        self.client.force_login(self.owner)

        dashboard = self.client.get(
            reverse('committee_dashboard', args=[self.event.pk])
        )
        assignment_manage = self.client.get(
            reverse('paper_assignment_manage', args=[self.paper.pk])
        )

        self.assertEqual(dashboard.status_code, 200)
        self.assertContains(dashboard, 'Comissao')
        self.assertEqual(assignment_manage.status_code, 200)

    def test_manager_can_remove_committee_member(self):
        manager = self.create_user('manager@example.com')
        member_user = self.create_user('member@example.com')
        CommitteeMember.objects.create(
            event=self.event,
            user=manager,
            is_manager=True,
        )
        member = CommitteeMember.objects.create(
            event=self.event,
            user=member_user,
            is_decider=True,
        )

        self.client.force_login(manager)
        response = self.client.post(
            reverse(
                'committee_member_delete',
                args=[self.event.pk, member.pk],
            )
        )

        self.assertRedirects(
            response,
            reverse('committee_dashboard', args=[self.event.pk]),
        )
        self.assertFalse(CommitteeMember.objects.filter(pk=member.pk).exists())

    def test_owner_committee_member_cannot_be_removed(self):
        owner_member = CommitteeMember.objects.create(
            event=self.event,
            user=self.owner,
            is_manager=True,
            is_decider=True,
        )

        self.client.force_login(self.owner)
        self.client.post(
            reverse(
                'committee_member_delete',
                args=[self.event.pk, owner_member.pk],
            )
        )

        self.assertTrue(
            CommitteeMember.objects.filter(pk=owner_member.pk).exists()
        )

    def test_reviewer_without_review_can_be_removed_with_pending_assignments(self):
        assignment = self.create_assignment()

        self.client.force_login(self.owner)
        response = self.client.post(
            reverse(
                'reviewer_delete',
                args=[self.event.pk, self.reviewer.pk],
            )
        )

        self.assertRedirects(
            response,
            reverse('committee_dashboard', args=[self.event.pk]),
        )
        self.assertFalse(Reviewer.objects.filter(pk=self.reviewer.pk).exists())
        self.assertFalse(
            ReviewAssignment.objects.filter(pk=assignment.pk).exists()
        )

    def test_reviewer_with_submitted_review_cannot_be_removed(self):
        assignment = self.create_assignment()
        self.submit_review(assignment)

        self.client.force_login(self.owner)
        self.client.post(
            reverse(
                'reviewer_delete',
                args=[self.event.pk, self.reviewer.pk],
            )
        )

        self.assertTrue(Reviewer.objects.filter(pk=self.reviewer.pk).exists())
        self.assertTrue(
            ReviewAssignment.objects.filter(pk=assignment.pk).exists()
        )

    def test_pending_assignment_can_be_removed(self):
        assignment = self.create_assignment()

        self.client.force_login(self.owner)
        response = self.client.post(
            reverse('review_assignment_delete', args=[assignment.pk])
        )

        self.assertRedirects(
            response,
            reverse('paper_assignment_manage', args=[self.paper.pk]),
        )
        self.assertFalse(
            ReviewAssignment.objects.filter(pk=assignment.pk).exists()
        )

    def test_assignment_with_review_cannot_be_removed(self):
        assignment = self.create_assignment()
        self.submit_review(assignment)

        self.client.force_login(self.owner)
        self.client.post(
            reverse('review_assignment_delete', args=[assignment.pk])
        )

        self.assertTrue(
            ReviewAssignment.objects.filter(pk=assignment.pk).exists()
        )

    def test_distribution_form_preserves_assignments_with_review(self):
        reviewed = self.create_assignment()
        pending = self.create_assignment(self.second_reviewer)
        self.submit_review(reviewed)

        form = AssignmentForm(
            {'reviewers': [self.second_reviewer.pk]},
            paper=self.paper,
        )

        self.assertFalse(form.is_valid())
        self.assertTrue(
            ReviewAssignment.objects.filter(pk=reviewed.pk).exists()
        )
        self.assertTrue(
            ReviewAssignment.objects.filter(pk=pending.pk).exists()
        )

    def test_event_detail_dashboard_is_visible_only_to_committee(self):
        CommitteeMember.objects.create(
            event=self.event,
            user=self.outsider,
            is_manager=True,
        )
        self.create_assignment()

        self.client.force_login(self.outsider)
        response = self.client.get(reverse('event_detail', args=[self.event.pk]))
        self.assertContains(response, 'Dashboard do evento')
        self.assertContains(response, 'Faltam avaliar')
        self.assertContains(response, 'Trabalhos individuais')
        self.assertContains(response, self.paper.title)
        self.assertContains(response, self.eixo.name)
        self.assertContains(response, '0/1')
        self.assertContains(response, self.reviewer_user.full_name)

        plain_user = self.create_user('plain@example.com')
        self.client.force_login(plain_user)
        response = self.client.get(reverse('event_detail', args=[self.event.pk]))
        self.assertNotContains(response, 'Dashboard do evento')
