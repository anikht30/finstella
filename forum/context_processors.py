# Shree Ganeshay Namahhhh.....

from .models import CustomUser, Thread, Category,Reply,Event,SubReply,EventRegistration,Notifications
from django.db.models import Count

# function for globally allowed data so i can use this data through out the web application

def global_forum_app_data(request):
    # if user logedin it should only make queries for data
    if request.user.is_authenticated:
         # 2. fetch all categories for sidebar

        categories = Category.objects.all().annotate(total_threads=Count('threads')).order_by('-total_threads')
        topics = Category.objects.all().annotate(total_threads=Count('threads')).order_by('-total_threads')[:5]
        # order_by(Thread.objects.all().count)

        bio_lenght_greter_then_100 = len(request.user.about or "") > 100
# members list
        members_list = CustomUser.objects.filter(is_active=True, is_superuser=False).order_by('first_name')[:5]
        members_count = CustomUser.objects.filter(is_active=True, is_superuser=False).count()

   #dashboard Card count

        active_discussion_count =  Thread.objects.all().count()  

        # reply count 
        total_response = Reply.objects.count()

        #open queries count

        open_queries_count = Thread.objects.select_related('author','category').filter(replies__isnull=True).count()


        #industry pulse percentage
        top_category = categories.first()
        total_threads = top_category.total_threads if top_category else 0
        active_discussion_count =  Thread.objects.all().count()  
        if active_discussion_count > 0:
            percentage = (total_threads/active_discussion_count) * 100
        else:
            percentage = 0


        # count only notifications for this specific user that are not read yet
        #unread_notifications_count = Notifications.objects.filter(recipient=request.user, is_read=False).count()
        unread_notifications_count = Notifications.objects.filter(recipient=request.user,badge_cleared=False).count()
        unread_notifications = Notifications.objects.filter(recipient=request.user, is_read=False)
        request = request
        return {'request':request,
            'active_discussion_count':active_discussion_count,
            'categories':categories,
            'members_list':members_list,
            'members_count':members_count,
            'total_response':total_response,
            'open_queries_count':open_queries_count,
            'percentage':percentage,
            'unread_notifications_count':unread_notifications_count,
            'unread_notifications':unread_notifications,
            'topics':topics,
            'bio_lenght_greter_then_100':bio_lenght_greter_then_100,



        }

    return{}
    