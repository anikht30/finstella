from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser,Category,Thread,Event,Reply,SubReply,EventRegistration,Notifications



class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ['email', 'username', 'title', 'company', 'is_active_subscriber','mobileno','middle_name']
    fieldsets = UserAdmin.fieldsets+(
        ('CFO Details',{'fields':('title','company','linkedin_url','is_active_subscriber','mobileno','middle_name')}),
    )

class categoryAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug':('name',)}

admin.site.register(CustomUser,CustomUserAdmin)
admin.site.register(Category,categoryAdmin)
admin.site.register(Thread)
# admin.site.register(Event)
admin.site.register(Reply)
admin.site.register(SubReply)



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