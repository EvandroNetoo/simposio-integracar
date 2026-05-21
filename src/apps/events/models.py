from accounts.models import User
from django.db import models


class Event(models.Model):
    owner = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True
    )
    name = models.CharField('nome do evento', max_length=255)
    edition = models.CharField('edicao', max_length=50)
    year = models.PositiveSmallIntegerField('ano')
    organizing_institution = models.CharField(
        'instituicao organizadora', max_length=255
    )
    submission_period_start = models.DateTimeField(
        'periodo de submissao (inicio)'
    )
    submission_period_end = models.DateTimeField('periodo de submissao (fim)')
    evaluation_period_start = models.DateTimeField(
        'periodo de avaliacao (inicio)'
    )
    evaluation_period_end = models.DateTimeField('periodo de avaliacao (fim)')
    results_publication_date = models.DateTimeField(
        'data de divulgacao dos resultados'
    )
    contact_email = models.EmailField('e-mail de contato da organizacao')
    submission_rules = models.TextField(
        'regras gerais de submissao', blank=True
    )
    blind_review = models.BooleanField(
        'revisao cega',
        default=False,
        help_text='Se ativado, os avaliadores não terão acesso às informações dos autores durante a avaliação.',
    )

    user_reviewers = models.ManyToManyField(
        User,
        related_name='events_as_reviewer',
        blank=True,
        through='reviews.Reviewer',
        verbose_name='avaliadores',
        help_text='Usuários que atuarão como avaliadores para este evento. Eles terão acesso às submissões durante o período de avaliação.',
    )

    class Meta:
        verbose_name = 'evento'
        verbose_name_plural = 'eventos'
        ordering = ['-year', 'name', 'edition']

    def __str__(self) -> str:
        return f'{self.name} ({self.edition}/{self.year})'


class EixoTematico(models.Model):
    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name='eixos_tematicos',
        verbose_name='evento',
    )
    name = models.CharField('nome do eixo temático', max_length=255)

    class Meta:
        verbose_name = 'eixo temático'
        verbose_name_plural = 'eixos temáticos'
        unique_together = ('name', 'event')

    def __str__(self) -> str:
        return f'{self.name} - {self.event}'
