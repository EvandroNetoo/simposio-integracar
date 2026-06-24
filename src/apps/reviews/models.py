from accounts.models import User
from django.core.exceptions import ValidationError
from django.db import models
from events.models import EixoTematico, Event
from papers.models import Coauthor, Paper


class CommitteeMember(models.Model):
    event = models.ForeignKey(
        Event,
        models.CASCADE,
        related_name='committee_members',
        verbose_name='evento',
    )
    user = models.ForeignKey(
        User,
        models.CASCADE,
        related_name='committee_memberships',
        verbose_name='usuario',
    )
    is_manager = models.BooleanField('gestor', default=False)
    is_decider = models.BooleanField('decisor', default=False)

    class Meta:
        verbose_name = 'membro da comissao'
        verbose_name_plural = 'membros da comissao'
        constraints = [
            models.UniqueConstraint(
                fields=('event', 'user'),
                name='unique_committee_member_per_event',
            )
        ]

    def __str__(self):
        return f'{self.user} - {self.event}'

    def clean(self):
        if not self.is_manager and not self.is_decider:
            raise ValidationError(
                'O membro deve ser gestor, decisor ou acumular os dois papeis.'
            )


class Reviewer(models.Model):
    event = models.ForeignKey(
        Event,
        models.CASCADE,
        related_name='reviewers',
        verbose_name='evento',
    )
    user = models.ForeignKey(
        User,
        models.CASCADE,
        verbose_name='avaliador',
    )
    eixos_tematicos = models.ManyToManyField(
        EixoTematico,
        blank=True,
        related_name='reviewers',
        verbose_name='eixos tematicos',
    )

    class Meta:
        verbose_name = 'avaliador do evento'
        verbose_name_plural = 'avaliadores do evento'
        constraints = [
            models.UniqueConstraint(
                fields=('event', 'user'),
                name='unique_reviewer_per_event',
            )
        ]

    def __str__(self) -> str:
        return f'{self.user} - {self.event}'


class ReviewAssignment(models.Model):
    reviewer = models.ForeignKey(
        Reviewer,
        models.CASCADE,
        related_name='assignments',
        verbose_name='avaliador',
    )
    paper = models.ForeignKey(
        Paper,
        models.CASCADE,
        related_name='review_assignments',
        verbose_name='trabalho',
    )
    assigned_at = models.DateTimeField(
        verbose_name='data de atribuicao',
        auto_now_add=True,
    )
    completed_at = models.DateTimeField(
        verbose_name='data de conclusao',
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = 'atribuicao de avaliador'
        verbose_name_plural = 'atribuicoes de avaliador'
        constraints = [
            models.UniqueConstraint(
                fields=('reviewer', 'paper'),
                name='unique_reviewer_assignment_per_paper',
            )
        ]

    def __str__(self):
        return f'{self.reviewer} - {self.paper}'

    def clean(self):
        errors = {}
        if self.reviewer_id and self.paper_id:
            if self.reviewer.event_id != self.paper.event_id:
                errors['reviewer'] = (
                    'O avaliador deve pertencer ao evento do trabalho.'
                )
            if self.reviewer.user_id == self.paper.user_id:
                errors['reviewer'] = (
                    'O autor principal nao pode avaliar o trabalho.'
                )
            if (
                Coauthor.objects.filter(
                    paper=self.paper,
                    user_id=self.reviewer.user_id,
                ).exists()
                or Coauthor.objects.filter(
                    paper=self.paper,
                    email__iexact=self.reviewer.user.email,
                ).exists()
            ):
                errors['reviewer'] = 'Um coautor nao pode avaliar o trabalho.'
        if errors:
            raise ValidationError(errors)


class Review(models.Model):
    class ReviewRecommendation(models.TextChoices):
        APPROVE = 'approve', 'Aprovar'
        APPROVE_WITH_CHANGES = (
            'approve_with_changes',
            'Aprovar com alteracoes',
        )
        REJECT = 'reject', 'Recusar'

    assignment = models.OneToOneField(
        ReviewAssignment,
        on_delete=models.CASCADE,
        related_name='review',
        verbose_name='atribuicao',
    )
    comments_to_author = models.TextField('comentarios ao autor')
    internal_comments = models.TextField(
        'comentarios internos',
        blank=True,
    )
    recommendation = models.CharField(
        'recomendacao',
        max_length=30,
        choices=ReviewRecommendation.choices,
    )
    submitted_at = models.DateTimeField('data do parecer', auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'avaliacao'
        verbose_name_plural = 'avaliacoes'

    def __str__(self):
        return f'{self.assignment.paper} - {self.assignment.reviewer}'


class FinalDecision(models.Model):
    class Result(models.TextChoices):
        APPROVED = 'approved', 'Aprovado'
        APPROVED_WITH_CHANGES = (
            'approved_with_changes',
            'Aprovado com alteracoes',
        )
        REJECTED = 'rejected', 'Recusado'

    paper = models.OneToOneField(
        Paper,
        models.CASCADE,
        related_name='final_decision',
        verbose_name='trabalho',
    )
    result = models.CharField(
        'resultado',
        max_length=30,
        choices=Result.choices,
    )
    justification = models.TextField('justificativa')
    decided_by = models.ForeignKey(
        User,
        models.PROTECT,
        related_name='review_decisions',
        verbose_name='decidido por',
    )
    published_at = models.DateTimeField('publicada em', auto_now_add=True)

    class Meta:
        verbose_name = 'decisao final'
        verbose_name_plural = 'decisoes finais'

    def __str__(self):
        return f'{self.paper} - {self.get_result_display()}'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        status_map = {
            self.Result.APPROVED: Paper.Status.APPROVED,
            self.Result.APPROVED_WITH_CHANGES: (
                Paper.Status.APPROVED_WITH_CHANGES
            ),
            self.Result.REJECTED: Paper.Status.REJECTED,
        }
        self.paper.status = status_map[self.result]
        self.paper.save(update_fields=('status',))


def user_can_manage_event(user, event):
    if not user.is_authenticated:
        return False
    if event.owner_id == user.id:
        return True
    return CommitteeMember.objects.filter(
        event=event,
        user=user,
        is_manager=True,
    ).exists()


def user_can_decide_event(user, event):
    if not user.is_authenticated:
        return False
    if event.owner_id == user.id:
        return True
    return CommitteeMember.objects.filter(
        event=event,
        user=user,
        is_decider=True,
    ).exists()
