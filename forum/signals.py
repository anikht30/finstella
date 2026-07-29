from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Reply,Notifications
from django.urls import reverse 


# This listens for any time a reply is saved to the database 

@receiver(post_save, sender=Reply)
def create_reply_notification(sender,instance,created, **kwargs):
    # create is true only when a reply is brand new (not just being edited)
    print("hello i am working")
    if created:
        thread_author = instance.thread.author
        reply_author = instance.author

        if thread_author != reply_author:
            Notifications.objects.create(
                recipient = thread_author,
                actor = reply_author,
                message = f"{reply_author.first_name} replied to your discussion : {instance.thread.title[:30]}....",
                # link = "f/thread/{instance.thread.id}/",
                link = reverse('thread_detail', args=[instance.thread.id])
            )

