from accounts.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from events.models import EixoTematico, Event


class Paper(models.Model):
    user = models.ForeignKey(
        User, models.CASCADE, related_name='papers', verbose_name='autor'
    )
    event = models.ForeignKey(
        Event, models.CASCADE, related_name='papers', verbose_name='evento'
    )
    eixo_tematico = models.ForeignKey(
        EixoTematico,
        models.PROTECT,
        related_name='papers',
        verbose_name='eixo temático',
    )
    title = models.CharField(max_length=255, verbose_name='título')
    abstract = models.TextField(verbose_name='resumo')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'trabalho'
        verbose_name_plural = 'trabalhos'

    def __str__(self):
        return self.title

    def clean(self):
        if (
            self.event_id
            and self.eixo_tematico_id
            and self.eixo_tematico.event_id != self.event_id
        ):
            raise ValidationError({
                'eixo_tematico': (
                    'Selecione um eixo temático do evento escolhido.'
                )
            })


class Coauthor(models.Model):
    class AffiliationType(models.TextChoices):
        STUDENT = 'student', 'Estudante'
        TEACHER = 'teacher', 'Professor'
        TECHNICIAN = 'technician', 'Tecnico'
        EXTERNAL_RESEARCHER = 'external_researcher', 'Pesquisador externo'
        OTHER = 'other', 'Outro'

    paper = models.ForeignKey(Paper, models.CASCADE, related_name='coauthors')
    user = models.ForeignKey(
        User,
        models.CASCADE,
        blank=True,
        null=True,
        related_name='coauthored',
        verbose_name='usuário',
    )
    name = models.CharField('nome', max_length=255, blank=True)
    email = models.EmailField(blank=True)
    institution = models.CharField(
        'instituicao de vinculo',
        max_length=255,
        blank=True,
    )
    affiliation_type = models.CharField(
        'tipo de vinculo',
        max_length=30,
        choices=AffiliationType.choices,
        blank=True,
    )
    authorship_order = models.PositiveIntegerField(
        'ordem de autoria', default=1
    )

    class Meta:
        verbose_name = 'coautor'
        verbose_name_plural = 'coautores'
        constraints = [
            models.UniqueConstraint(
                fields=['paper', 'user'],
                condition=Q(user__isnull=False),
                name='uniq_coauthor_paper_user',
            ),
            models.UniqueConstraint(
                fields=['paper', 'email'],
                condition=Q(user__isnull=True),
                name='uniq_coauthor_paper_email',
            ),
        ]
        ordering = ('authorship_order',)

    def __str__(self):
        if self.user_id:
            return self.user.email
        return self.name or self.email

    def clean(self):
        if self.user_id == self.paper.user_id:
            raise ValidationError(
                'O autor principal do trabalho não pode ser adicionado como coautor.'
            )

        has_user = self.user_id

        if has_user and any([
            self.name,
            self.email,
            self.institution,
            self.affiliation_type,
        ]):
            raise ValidationError(
                'Não preencha os campos de nome, email, instituição '
                'e tipo de vínculo para coautores com usuário associado.'
            )
        if not has_user and not all([
            self.name,
            self.email,
            self.institution,
            self.affiliation_type,
        ]):
            raise ValidationError(
                'Preencha os campos de nome, email, instituição e '
                'tipo de vínculo para coautores sem usuário associado.'
            )


class Submission(models.Model):
    paper = models.ForeignKey(Paper, models.CASCADE)
    file = models.FileField(upload_to='submissions/')
    observations = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'submissão'
        verbose_name_plural = 'submissões'

    def __str__(self):
        return f'Submission by {self.paper.user.email} at {self.created_at}'
