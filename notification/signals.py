from django.contrib.auth.models import User
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from .models import ChatMessages, Notifications, Profile


@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created:
        print('---------------------->>>>>', instance)
        data = {"message":"Signal Message","group_name":"signaltest","socket_desc":"Signal Test"}
        test = ChatMessages.objects.create(**data)
        test.save()
        print(test.message)

