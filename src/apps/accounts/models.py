from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from accounts.managers import CustomUserManager


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(_('e-mail'), unique=True)
    first_name = models.CharField('nome', max_length=30)
    surname = models.CharField('sobrenome', max_length=100)

    is_staff = models.BooleanField(
        _('staff status'),
        default=False,
        help_text=_(
            'Designates whether the user can log into this admin site.'
        ),
    )
    is_active = models.BooleanField(
        _('active'),
        default=True,
        help_text=_(
            'Designates whether this user should be treated as active. '
            'Unselect this instead of deleting accounts.'
        ),
    )
    date_joined = models.DateTimeField(_('date joined'), default=timezone.now)

    USERNAME_FIELD = 'email'

    objects = CustomUserManager()

    profile: Profile

    class Meta:
        verbose_name = 'usuário'
        verbose_name_plural = 'usuários'

    def __str__(self):
        return self.email

    @property
    def full_name(self):
        return f'{self.first_name} {self.surname}'.strip()


class Profile(models.Model):
    class AffiliationType(models.TextChoices):
        STUDENT = 'student', 'Estudante'
        TEACHER = 'teacher', 'Professor'
        TECHNICIAN = 'technician', 'Tecnico'
        EXTERNAL_RESEARCHER = 'external_researcher', 'Pesquisador externo'
        OTHER = 'other', 'Outro'

    user = models.OneToOneField(
        User,
        models.CASCADE,
        verbose_name='usuario',
        related_name='profile',
    )
    cpf = models.CharField('CPF', max_length=14, blank=True)
    phone = models.CharField('telefone', max_length=15, blank=True)
    institution = models.CharField(
        'instituicao de vinculo', max_length=255, blank=True
    )
    affiliation_type = models.CharField(
        'tipo de vinculo',
        max_length=30,
        choices=AffiliationType.choices,
        blank=True,
    )
    education_level = models.CharField(
        'nivel de formacao', max_length=100, blank=True
    )
    academic_title = models.CharField('titulacao', max_length=100, blank=True)
    city = models.CharField('cidade', max_length=120, blank=True)
    state = models.CharField('estado', max_length=2, blank=True)
    lattes_url = models.URLField('link do lattes', blank=True)
    areas_of_activity = models.TextField('areas de atuacao', blank=True)

    class Meta:
        verbose_name = 'perfil'
        verbose_name_plural = 'perfis'

    def __str__(self):
        return f'{self.user.email}'
