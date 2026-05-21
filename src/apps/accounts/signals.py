from django.db.models.signals import post_save
from django.dispatch import receiver

from accounts.models import Profile, User


@receiver(post_save, sender=User)
def ensure_user_profile(
    sender: type[User], instance: User, created: bool, **kwargs
):
    if created:
        Profile.objects.create(user=instance)
        return
    Profile.objects.get_or_create(user=instance)
