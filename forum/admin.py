from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser,Category,Thread,Event,Reply,SubReply



class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ['email', 'username', 'title', 'company', 'is_active_subscriber']
    fieldsets = UserAdmin.fieldsets+(
        ('CFO Details',{'fields':('title','company','linkedin_url','is_active_subscriber')}),
    )

class categoryAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug':('name',)}

admin.site.register(CustomUser,CustomUserAdmin)
admin.site.register(Category,categoryAdmin)
admin.site.register(Thread)
admin.site.register(Event)
admin.site.register(Reply)
admin.site.register(SubReply)