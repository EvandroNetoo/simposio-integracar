from accounts.models import User
from django.core.exceptions import ValidationError
from django.db import models


class Paper(models.Model):
    user = models.ForeignKey(User, models.CASCADE)
    title = models.CharField(max_length=255)
    abstract = models.TextField()
    authors = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


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
    )
    name = models.CharField('nome', max_length=255)
    email = models.EmailField()
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

    def __str__(self):
        return self.user.email

    def clean(self):
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

    def __str__(self):
        return f'Submission by {self.paper.user.email} at {self.created_at}'
