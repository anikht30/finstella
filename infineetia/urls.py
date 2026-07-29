"""
URL configuration for infineetia project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from forum.views import landing_page,apply_view,userexists,login_view,logout_view,dashboard_view,thread_detail_view,create_thread_view,member_directory_view,add_subreply,profile_view,edit_profile,member_profile
from forum.views import all_active_discussion_view,all_new_discussion_view,my_discussion_view,events_page,create_event,register_for_event
from forum.views import mark_notification_read
#template view to quickly show temporary dashboard
from django.views.generic import TemplateView
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', landing_page, name='landing_page'),
    path('apply/',apply_view, name='apply'),
    path('userexists/',userexists, name='userexists'),
    path('login/',login_view, name='login'),
    path('logout/',logout_view,name='logout'),

    #dashboard
    path('dashboard/', dashboard_view, name='dashboard'),
    path('thread/<int:thread_id>/', thread_detail_view, name='thread_detail'),
    path('thread/new/',create_thread_view, name='create_thread'),
    path('members/',member_directory_view,name='member_directory'),
    path('sw.js', TemplateView.as_view(template_name="sw.js", content_type='application/javascript'), name='sw.js'),
    path('reply/<int:reply_id>/respond/',add_subreply,name="add_subreply"),
    path('profile/',profile_view,name="profile"),
    path('profile/edit/',edit_profile,name='edit_profile'),
    path('member/<int:user_id>/',member_profile,name='member_profile'),
    path('fellowship/',TemplateView.as_view(template_name='fellowship.html'),name='fellowship'),
    path('active_discussion/',all_active_discussion_view,name="active_discussion"),
    path('open_queries/',all_new_discussion_view,name="open_queries"),
    path('my_discussion/',my_discussion_view,name="my_discussion"),
    path('events/', events_page, name='events_page'),
    path('events/create/', create_event, name='create_event'),
    path('events/register/', register_for_event, name='register_for_event'),
    path('notifications/read/<int:notification_id>',mark_notification_read,name='mark_notification_read'),

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)



