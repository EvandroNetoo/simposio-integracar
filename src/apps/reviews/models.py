from decimal import Decimal

from accounts.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Sum
from django.utils import timezone
from events.models import EixoTematico, Event
from papers.models import Coauthor, Paper, Submission


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
        verbose_name='usuário',
    )
    is_manager = models.BooleanField('gestor', default=False)
    is_decider = models.BooleanField('decisor', default=False)

    class Meta:
        verbose_name = 'membro da comissão'
        verbose_name_plural = 'membros da comissão'
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
                'O membro deve ser gestor, decisor ou acumular os dois papéis.'
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
        verbose_name='eixos temáticos',
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


class ReviewInstrument(models.Model):
    event = models.ForeignKey(
        Event,
        models.CASCADE,
        related_name='review_instruments',
        verbose_name='evento',
    )
    version = models.PositiveIntegerField('versão')
    name = models.CharField('nome', max_length=255, default='Avaliação')
    created_by = models.ForeignKey(
        User,
        models.PROTECT,
        related_name='created_review_instruments',
        verbose_name='criado por',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'instrumento de avaliação'
        verbose_name_plural = 'instrumentos de avaliação'
        ordering = ('event', '-version')
        constraints = [
            models.UniqueConstraint(
                fields=('event', 'version'),
                name='unique_review_instrument_version',
            )
        ]

    def __str__(self):
        return f'{self.name} v{self.version} - {self.event}'

    @property
    def is_used(self):
        return self.rounds.exists()

    def clean(self):
        if self.pk and self.is_used:
            original = ReviewInstrument.objects.get(pk=self.pk)
            if self.name != original.name:
                raise ValidationError(
                    'Instrumentos já utilizados não podem ser alterados.'
                )


class ReviewCriterion(models.Model):
    instrument = models.ForeignKey(
        ReviewInstrument,
        models.CASCADE,
        related_name='criteria',
        verbose_name='instrumento',
    )
    name = models.CharField('nome', max_length=255)
    description = models.TextField('descrição', blank=True)
    weight = models.DecimalField(
        'peso percentual',
        max_digits=5,
        decimal_places=2,
    )
    order = models.PositiveSmallIntegerField('ordem', default=1)

    class Meta:
        verbose_name = 'critério de avaliação'
        verbose_name_plural = 'critérios de avaliação'
        ordering = ('order', 'id')
        constraints = [
            models.UniqueConstraint(
                fields=('instrument', 'order'),
                name='unique_criterion_order_per_instrument',
            ),
            models.CheckConstraint(
                condition=models.Q(weight__gt=0) & models.Q(weight__lte=100),
                name='criterion_weight_between_zero_and_100',
            ),
        ]

    def __str__(self):
        return self.name

    def clean(self):
        if self.instrument_id and self.instrument.is_used:
            if not self.pk:
                raise ValidationError(
                    'Não é possível adicionar critérios a um instrumento usado.'
                )
            original = ReviewCriterion.objects.get(pk=self.pk)
            changed = any(
                getattr(self, field) != getattr(original, field)
                for field in ('name', 'description', 'weight', 'order')
            )
            if changed:
                raise ValidationError(
                    'Critérios de instrumentos usados não podem ser alterados.'
                )


class ReviewRound(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Rascunho'
        OPEN = 'open', 'Aberta'
        CLOSED = 'closed', 'Encerrada'
        DECIDED = 'decided', 'Decidida'

    paper = models.ForeignKey(
        Paper,
        models.CASCADE,
        related_name='review_rounds',
        verbose_name='trabalho',
    )
    submission = models.OneToOneField(
        Submission,
        models.PROTECT,
        related_name='review_round',
        verbose_name='versão avaliada',
    )
    instrument = models.ForeignKey(
        ReviewInstrument,
        models.PROTECT,
        related_name='rounds',
        verbose_name='instrumento',
    )
    number = models.PositiveSmallIntegerField('número da rodada')
    starts_at = models.DateTimeField('início')
    ends_at = models.DateTimeField('fim')
    status = models.CharField(
        'situação',
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    created_by = models.ForeignKey(
        User,
        models.PROTECT,
        related_name='created_review_rounds',
        verbose_name='criada por',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'rodada de avaliação'
        verbose_name_plural = 'rodadas de avaliação'
        ordering = ('paper', 'number')
        constraints = [
            models.UniqueConstraint(
                fields=('paper', 'number'),
                name='unique_review_round_number_per_paper',
            )
        ]

    def __str__(self):
        return f'{self.paper} - rodada {self.number}'

    def clean(self):
        errors = {}
        if self.submission_id and self.paper_id:
            if self.submission.paper_id != self.paper_id:
                errors['submission'] = 'A versão deve pertencer ao trabalho.'
            latest_id = (
                self.paper.submission_set
                .order_by('-version')
                .values_list('id', flat=True)
                .first()
            )
            if (
                self.status == self.Status.DRAFT
                and latest_id != self.submission_id
            ):
                errors['submission'] = 'Selecione a versão mais recente.'
        if (
            self.instrument_id
            and self.paper_id
            and self.instrument.event_id != self.paper.event_id
        ):
            errors['instrument'] = (
                'O instrumento deve pertencer ao evento do trabalho.'
            )
        if self.starts_at and self.ends_at and self.starts_at >= self.ends_at:
            errors['ends_at'] = 'O fim deve ser posterior ao início.'
        if errors:
            raise ValidationError(errors)

    @property
    def is_editable(self):
        now = timezone.now()
        return (
            self.status == self.Status.OPEN
            and self.starts_at <= now <= self.ends_at
        )

    def open(self):
        if self.status != self.Status.DRAFT:
            raise ValidationError(
                'Somente rodadas em rascunho podem ser abertas.'
            )
        criteria_weight = self.instrument.criteria.aggregate(
            total=Sum('weight')
        )['total']
        if criteria_weight != Decimal('100'):
            raise ValidationError(
                'Os pesos dos critérios devem totalizar 100%.'
            )
        if self.assignments.count() < self.paper.event.minimum_reviewers:
            raise ValidationError(
                'A rodada não possui a quantidade mínima de avaliadores.'
            )
        self.full_clean()
        self.status = self.Status.OPEN
        self.save(update_fields=('status',))
        self.paper.status = Paper.Status.UNDER_REVIEW
        self.paper.save(update_fields=('status',))

    def close(self):
        if self.status != self.Status.OPEN:
            raise ValidationError(
                'Somente rodadas abertas podem ser encerradas.'
            )
        self.status = self.Status.CLOSED
        self.save(update_fields=('status',))
        self.paper.status = Paper.Status.REVIEW_COMPLETED
        self.paper.save(update_fields=('status',))


class ReviewAssignment(models.Model):
    reviewer = models.ForeignKey(
        Reviewer,
        models.CASCADE,
        related_name='assignments',
        verbose_name='avaliador',
    )
    round = models.ForeignKey(
        ReviewRound,
        models.CASCADE,
        related_name='assignments',
        verbose_name='rodada',
        null=True,
        blank=True,
    )
    paper = models.ForeignKey(
        Paper,
        models.CASCADE,
        related_name='legacy_review_assignments',
        verbose_name='trabalho legado',
        null=True,
        blank=True,
    )
    assigned_at = models.DateTimeField(
        verbose_name='data de atribuição',
        auto_now_add=True,
    )
    completed_at = models.DateTimeField(
        verbose_name='data de conclusão',
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = 'atribuição de avaliador'
        verbose_name_plural = 'atribuições de avaliador'
        constraints = [
            models.UniqueConstraint(
                fields=('reviewer', 'round'),
                name='unique_reviewer_assignment_per_round',
            )
        ]

    def __str__(self):
        return f'{self.reviewer} - {self.round or self.paper}'

    def clean(self):
        errors = {}
        if self.reviewer_id and self.round_id:
            paper = self.round.paper
            if self.reviewer.event_id != paper.event_id:
                errors['reviewer'] = (
                    'O avaliador deve pertencer ao evento do trabalho.'
                )
            if self.reviewer.user_id == paper.user_id:
                errors['reviewer'] = (
                    'O autor principal não pode avaliar o trabalho.'
                )
            if (
                Coauthor.objects.filter(
                    paper=paper,
                    user_id=self.reviewer.user_id,
                ).exists()
                or Coauthor.objects.filter(
                    paper=paper,
                    email__iexact=self.reviewer.user.email,
                ).exists()
            ):
                errors['reviewer'] = 'Um coautor não pode avaliar o trabalho.'
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if self.round_id:
            self.paper_id = self.round.paper_id
        super().save(*args, **kwargs)


class Review(models.Model):
    class ReviewRecommendation(models.TextChoices):
        ACCEPT = 'accept', 'Aceitar'
        ACCEPT_WITH_CHANGES = (
            'accept_with_changes',
            'Aceitar com correções',
        )
        REJECT = 'reject', 'Rejeitar'

    assignment = models.OneToOneField(
        ReviewAssignment,
        on_delete=models.CASCADE,
        related_name='review',
        verbose_name='atribuição',
    )
    weighted_score = models.DecimalField(
        'média ponderada',
        max_digits=4,
        decimal_places=2,
        editable=False,
        null=True,
        blank=True,
    )
    score = models.DecimalField(
        'nota legada',
        max_digits=4,
        decimal_places=2,
        null=True,
        blank=True,
    )
    comments_to_author = models.TextField('comentários ao autor')
    internal_comments = models.TextField(
        'comentários internos',
        blank=True,
    )
    recommendation = models.CharField(
        'recomendação',
        max_length=30,
        choices=ReviewRecommendation.choices,
    )
    submitted_at = models.DateTimeField('data do parecer', auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'avaliação'
        verbose_name_plural = 'avaliações'

    def __str__(self):
        return f'{self.assignment.paper} - {self.assignment.reviewer}'

    def calculate_weighted_score(self):
        total = sum(
            item.score * item.criterion.weight / Decimal('100')
            for item in self.criterion_scores.select_related('criterion')
        )
        return Decimal(total).quantize(Decimal('0.01'))


class CriterionScore(models.Model):
    review = models.ForeignKey(
        Review,
        models.CASCADE,
        related_name='criterion_scores',
        verbose_name='avaliação',
    )
    criterion = models.ForeignKey(
        ReviewCriterion,
        models.PROTECT,
        related_name='scores',
        verbose_name='critério',
    )
    score = models.DecimalField(
        'nota',
        max_digits=4,
        decimal_places=2,
    )

    class Meta:
        verbose_name = 'nota de critério'
        verbose_name_plural = 'notas de critérios'
        constraints = [
            models.UniqueConstraint(
                fields=('review', 'criterion'),
                name='unique_score_per_review_criterion',
            ),
            models.CheckConstraint(
                condition=models.Q(score__gte=0) & models.Q(score__lte=10),
                name='criterion_score_between_zero_and_10',
            ),
        ]

    def clean(self):
        if (
            self.review_id
            and self.criterion_id
            and self.criterion.instrument_id
            != self.review.assignment.round.instrument_id
        ):
            raise ValidationError(
                'O critério não pertence ao instrumento desta rodada.'
            )


class FinalDecision(models.Model):
    class Result(models.TextChoices):
        APPROVED = 'approved', 'Aprovado'
        APPROVED_WITH_CHANGES = (
            'approved_with_changes',
            'Aprovado com correções',
        )
        REJECTED = 'rejected', 'Reprovado'

    round = models.OneToOneField(
        ReviewRound,
        models.CASCADE,
        related_name='decision',
        verbose_name='rodada',
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
        verbose_name = 'decisão final'
        verbose_name_plural = 'decisões finais'

    def __str__(self):
        return f'{self.round} - {self.get_result_display()}'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.round.status = ReviewRound.Status.DECIDED
        self.round.save(update_fields=('status',))
        status_map = {
            self.Result.APPROVED: Paper.Status.APPROVED,
            self.Result.APPROVED_WITH_CHANGES: (
                Paper.Status.APPROVED_WITH_CHANGES
            ),
            self.Result.REJECTED: Paper.Status.REJECTED,
        }
        self.round.paper.status = status_map[self.result]
        self.round.paper.save(update_fields=('status',))


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
