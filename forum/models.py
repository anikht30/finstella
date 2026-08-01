from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.files import File
from PIL import Image
from io import BytesIO
import os
from django.conf import settings #Safely connect to your CustomUser/Profile model


class CustomUser(AbstractUser):
    #password will set after register in background
    title = models.CharField(max_length=100, blank=True, null=True, help_text="e.g. CFO, Finance Director")
    company= models.CharField(max_length=150,blank=True,null=True)
    linkedin_url=models.CharField(max_length=200, blank=True, null=True)

    is_active_subscriber = models.BooleanField(default=False)

    profile_picture = models.ImageField(upload_to='avatars/', null=True, blank=True)
    about = models.TextField(null=True, blank=True, help_text='A Brief executive bio.')
    mobileno = models.CharField(max_length=15, blank=True, null=True)
    middle_name=models.CharField(max_length=150,blank=True,null=True)

    # def save(self, *args, **kwargs):
    #     # 1. CHECK IF THE IMAGE IS NEW
    #     # We only want to compress the image if they just uploaded a new one. 
    #     # If they are just updating their name/bio, we skip this to save CPU!
    #     is_new_image = False
    #     if self.pk:
    #         try:
    #             old_profile = CustomUser.objects.get(pk=self.pk)
    #             if old_profile.profile_picture != self.profile_picture:
    #                 is_new_image = True
    #         except CustomUser.DoesNotExist:
    #             is_new_image = True
    #     else:
    #         is_new_image = True

    #     # 2. PROCESS THE IMAGE
    #     if is_new_image and self.profile_picture:
    #         # Open the uploaded image file
    #         img = Image.open(self.profile_picture)
            
    #         # Ensure it's in a color mode that WEBP can handle safely
    #         if img.mode not in ('RGB', 'RGBA'):
    #             img = img.convert('RGB')

    #         # --- AUTO CENTER CROP MATH ---
    #         width, height = img.size
    #         if width != height:
    #             min_dim = min(width, height)
    #             left = (width - min_dim) / 2
    #             top = (height - min_dim) / 2
    #             right = (width + min_dim) / 2
    #             bottom = (height + min_dim) / 2
    #             img = img.crop((left, top, right, bottom))
            
    #         # --- RESIZE ---
    #         # Note: In modern Pillow, Image.LANCZOS is available as Image.Resampling.LANCZOS
    #         img = img.resize((256, 256), Image.Resampling.LANCZOS if hasattr(Image, 'Resampling') else Image.LANCZOS)
            
    #         # --- SAVE TO MEMORY BUFFER ---
    #         output = BytesIO()
    #         img.save(output, format='WEBP', quality=80, optimize=True)
    #         output.seek(0) # Reset the buffer cursor to the beginning
            
    #         # --- RENAME AND OVERWRITE ---
    #         # Strip the old extension (.jpg, .png) and force it to be .webp
    #         original_name = os.path.basename(self.profile_picture.name)
    #         file_name = f"{os.path.splitext(original_name)[0]}.webp"
            
    #         # Overwrite the Django ImageField with our new optimized file in memory
    #         self.profile_picture = File(output, name=file_name)

    #  # 3. RUN STANDARD DJANGO SAVE
    #     super().save(*args, **kwargs)
    def __str__(self):
        return f"{self.first_name} {self.last_name} {self.company}"    
    

class Category(models.Model):
    name = models.CharField(max_length=50)
    slug = models.SlugField(unique=True)

    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name_plural = "Categories"


class Thread(models.Model):
    title = models.CharField(max_length=255)
    content=models.TextField(default="No content provided")
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='threads')
    # connects the thread to the user who wrote it 
    author = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='threads')

    # Automatically records when thread was posted

    created_at = models.DateTimeField(auto_now_add=True)
    upvotes = models.IntegerField(default=0)
    is_pinned = models.BooleanField(default=False)

    @property
    def unique_author_count(self):
        # Counts the unique author IDs from all replies attached to this thread
        return self.replies.values('author').distinct().count()

    def __str__(self):
        return self.title


# class Event(models.Model):
#     EVENT_TYPES = [
#         ('Webinar','Webinar'),
#         ('In-person','In-person')
#     ]

#     title = models.CharField(max_length=200)
#     date = models.DateTimeField()
#     event_type=models.CharField(max_length=20, choices=EVENT_TYPES)

#     # Allow multiple users to rsvp to multiple events

#     def __str__(self):
#         return f"{self.title} - {self.date.strftime('%B %d, %Y')}"


class Reply(models.Model):
    # This links the reply strictly to one specific thread
    thread = models.ForeignKey(Thread, on_delete=models.CASCADE, related_name='replies')
    # this link the reply to cfo who wrote it 
    author = models.ForeignKey(CustomUser, on_delete=models.CASCADE)

    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Reply by {self.author.first_name} on {self.thread.title}"
    

class SubReply(models.Model):
    # This links the reply to one specific reply

    reply = models.ForeignKey(Reply, on_delete=models.CASCADE, related_name='sub_replies') 
    # this link the reply to cfo who wrote it 
    author = models.ForeignKey(CustomUser, on_delete=models.CASCADE)

    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)




class Event(models.Model):
    EVENT_TYPES=(
       ('WEBINAR', 'Webinar (Online)'),
       ('EVENT', 'Event (In-Person)'),
    )

    # 1. The Core Details
    title = models.CharField(max_length=200, verbose_name="Topic")
    description = models.TextField(verbose_name="Summary / Brief")
    event_type = models.CharField(max_length=20, choices=EVENT_TYPES, default='WEBINAR')
    
    # 2. Date and Time
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(blank=True, null=True) 
    
    # 3. Dynamic Fields (Shown based on Webinar vs Event)
    location = models.CharField(max_length=255, blank=True, null=True, help_text="City or Full Address (For Events)")
    meeting_link = models.URLField(blank=True, null=True, help_text="Zoom, Meet, or Teams link (For Webinars)")
    participation_fee = models.CharField(max_length=100, blank=True, null=True, help_text="e.g., 'Free', '$50', '₹1500'")
    
    # 4. Background Data (User never types this!)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='hosted_events')
    
    # 5. Moderation & Limits
    is_approved = models.BooleanField(default=False, help_text="Must be checked by Admin for the event to show publicly.")
    max_attendees = models.PositiveIntegerField(blank=True, null=True, help_text="Leave blank for unlimited.")
    
    # 6. Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-start_time'] # Shows newest events first

    def __str__(self):
        return f"[{self.get_event_type_display()}] {self.title}"


class EventRegistration(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='event_registrations')
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='registrations')
    registered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # CRITICAL: This prevents a user from registering for the exact same event twice!
        unique_together = ('user', 'event')

    def __str__(self):
        return f"{self.user.first_name} registered for: {self.event.title}"




# class for the notification table

class Notifications(models.Model):
    # 1. who receives the notification?
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")

    # 2. who triggered it? 

    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="actions", null=True, blank=True)

    # what dose it say?

    message = models.CharField(max_length=255)

    # where do it goes when it clicked?

    link = models.CharField(max_length=255, null=True, blank=True)

    # has the user seen it yet 

    is_read = models.BooleanField(default=False)

    # notification crete time

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at'] # show newest notification first

    def __str__(self):
        return f"To {self.recipient.first_name}: {self.message}"




class Feedback(models.Model):
    TYPES = (
        ('Feature Request', 'Feature Request'),
        ('Bug Report', 'Bug Report'),
        ('Community Suggestion', 'Community Suggestion'),
        )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    feedback_type = models.CharField(max_length=50, choices=TYPES)
    title = models.CharField(max_length=200)
    details = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.feedback_type}] {self.title} by {self.user.first_name}"