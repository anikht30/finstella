from django.contrib import admin
from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth import get_user_model
from .models import CustomUser,Category,Thread,Event,Reply,SubReply,EventRegistration,Notifications,Feedback
from django.utils.crypto import get_random_string
from django.contrib import messages



User = get_user_model()

@admin.action(description="Approve users, generate password & send payment link")
def approve_and_email_users(modeladmin, request, queryset):
    for user in queryset:
        # 1. Generate a secure 10-character temporary password
        dummy_password = get_random_string(length=10)
        
        # 2. Assign the password and mark the user as active/approved
        user.set_password(dummy_password)
        user.is_active = True 
        user.save()

        # Build the absolute URL for the checkout page
        checkout_url = request.build_absolute_uri('/login/')
        
        subject = "Application Approved! Welcome to Finstella"
        
        # 3. Update the email to include the dummy password
        message = (
            f"Hello {user.first_name},\n\n"
            f"Congratulations! Your application to join Finstella has been approved.\n\n"
            f"Your account has been provisioned with a temporary password. "
            f"You can log in using this password and change it from your profile settings later on.\n\n"
            f"Your temporary password: {dummy_password}\n\n"
            f"To activate your account and gain access to the network, please follow the link below to complete your subscription payment:\n\n"
            f"{checkout_url}\n\n"
            f"We look forward to seeing you inside.\n\n"
            f"Best regards,\n"
            f"The Finstella Team"
        )
        
        # Send via your live SMTP
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )
        
    messages.success(request, f"Successfully approved, generated passwords, and emailed {queryset.count()} users.")

class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ['email', 'username', 'title', 'company', 'is_active_subscriber','mobileno','middle_name','profile_picture']
    fieldsets = UserAdmin.fieldsets+(
        ('CFO Details',{'fields':('title','company','linkedin_url','is_active_subscriber','mobileno','middle_name','profile_picture')}),
    )
    actions = [approve_and_email_users]

class categoryAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug':('name',)}


admin.site.register(CustomUser,CustomUserAdmin)
admin.site.register(Category,categoryAdmin)
admin.site.register(Thread)
# admin.site.register(Event)
admin.site.register(Reply)
admin.site.register(SubReply)
admin.site.register(Feedback)


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    # What columns show up in the admin list view
    list_display = ('title', 'event_type', 'start_time', 'author', 'is_approved')
    
    # Adds a sidebar filter so you can quickly find "Unapproved" events
    list_filter = ('is_approved', 'event_type', 'start_time')
    
    # Adds a search bar
    search_fields = ('title', 'description', 'author__first_name', 'author__email')
    
    # Custom Action to approve multiple events at once
    actions = ['approve_selected_events']

    def approve_selected_events(self, request, queryset):
        # Flips is_approved to True for all checked boxes
        updated_count = queryset.update(is_approved=True)
        self.message_user(request, f"Successfully approved {updated_count} events.")
    
    approve_selected_events.short_description = "Approve selected events/webinars"


@admin.register(EventRegistration)
class EventRegistrationAdmin(admin.ModelAdmin):
    list_display = ('user', 'event', 'registered_at')
    list_filter = ('event__title',)
    search_fields = ('user__first_name', 'user__email', 'event__title')


@admin.register(Notifications)
class NotificationAdmin(admin.ModelAdmin):
    list_display=('recipient','message','is_read','created_at')
    list_filter=('is_read',)