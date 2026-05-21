from accounts.models import User
from django.db import models
from events.models import EixoTematico, Event
from papers.models import Paper


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
        unique_together = ('event', 'user')

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
        verbose_name='data de atribuição', auto_now_add=True
    )
    completed_at = models.DateTimeField(
        verbose_name='data de conclusão', null=True, blank=True
    )

    class Meta:
        verbose_name = 'atribuição de avaliador'
        verbose_name_plural = 'atribuições de avaliador'
        unique_together = (
            'reviewer',
            'paper',
        )


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
    score = models.DecimalField(
        verbose_name='nota',
        max_digits=4,
        decimal_places=2,
        null=True,
        blank=True,
    )

    comments_to_author = models.TextField(
        verbose_name='comentários ao autor',
    )
    internal_comments = models.TextField(
        verbose_name='comentários internos',
        blank=True,
    )
    recommendation = models.CharField(
        verbose_name='recomendação',
        max_length=30,
        choices=ReviewRecommendation.choices,
    )
    submitted_at = models.DateTimeField(
        verbose_name='data do parecer',
        auto_now_add=True,
    )
    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        verbose_name = 'avaliação'
        verbose_name_plural = 'avaliações'

    def __str__(self):
        return f'{self.assignment.paper} - {self.assignment.reviewer}'
