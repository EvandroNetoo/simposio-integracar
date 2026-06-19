from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import User


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    STORAGES={
        'default': {
            'BACKEND': 'django.core.files.storage.FileSystemStorage',
        },
        'staticfiles': {
            'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage',
        },
    },
)
class PasswordResetTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='author@example.com',
            password='old-password',  # noqa: S106
            first_name='Author',
            surname='User',
        )

    def test_password_reset_pages_are_public(self):
        response = self.client.get(reverse('password_reset'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Recuperar senha')

    def test_password_reset_post_sends_email(self):
        response = self.client.post(
            reverse('password_reset'),
            {'email': self.user.email},
        )

        self.assertRedirects(response, reverse('password_reset_done'))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(self.user.email, mail.outbox[0].to)
