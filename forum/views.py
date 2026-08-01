from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, get_user_model
from .models import CustomUser, Thread, Category,Reply,Event,SubReply,EventRegistration,Notifications,Feedback
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .forms import ProfileUpdateForm
from django.core.paginator import Paginator
from django.db.models import Q
from django.db.models import Count


User = get_user_model()


@login_required
def events_page(request):
    # 1. Fetch only the approved events
    upcoming_events = Event.objects.filter(is_approved=True)#.order_range(['start_time'])
    
    # 2. Get a list of IDs for events this user is already registered for
    # (This allows us to change the "Register" button to "Registered" on the front end)
    registered_event_ids = EventRegistration.objects.filter(user=request.user).values_list('event_id', flat=True)
    
    context = {
        'events': upcoming_events,
        'registered_event_ids': registered_event_ids
    }
    return render(request, 'events_list.html', context)


@login_required
def create_event(request):
    if request.method == "POST":
        # 1. Manually grab the data from the HTML popup form
        title = request.POST.get('title')
        description = request.POST.get('description')
        event_type = request.POST.get('event_type')
        start_time = request.POST.get('start_time')
        end_time = request.POST.get('end_time')
        
        # Grab the conditional fields based on what they picked
        location = request.POST.get('location') if event_type == 'EVENT' else None
        participation_fee = request.POST.get('participation_fee') if event_type == 'EVENT' else None
        meeting_link = request.POST.get('meeting_link') if event_type == 'WEBINAR' else None

        # 2. Create the Event in the database
        Event.objects.create(
            title=title,
            description=description,
            event_type=event_type,
            start_time=start_time,
            end_time=end_time,
            location=location,
            participation_fee=participation_fee,
            meeting_link=meeting_link,
            author=request.user,
            is_approved=False # Forces it to wait for admin approval
        )
        
        # 3. Add a success message to show the user
        messages.success(request, "Your event was submitted successfully! Our team will review it shortly.")
        
        # 4. Redirect them back to the events page
        return redirect('events_page')
        
    return redirect('events_page')




@login_required
def register_for_event(request):
    if request.method == "POST":
        event_id = request.POST.get('event_id')
        event = get_object_or_404(Event, id=event_id)
        
        # get_or_create safely creates the registration, or ignores it if they already registered
        registration, created = EventRegistration.objects.get_or_create(
            user=request.user,
            event=event
        )
        
        if created:
            messages.success(request, f"You have successfully registered for {event.title}!")
        else:
            messages.info(request, "You are already registered for this event.")
            
    return redirect('events_page')


def landing_page(request):

    member_count=CustomUser.objects.filter(is_active=True, is_superuser=False).count()
    threads = Thread.objects.select_related('author','category').order_by('-created_at')[:2]
    thread_count=Thread.objects.count()
    event_count = Event.objects.count()
    
    context = {
        'member_count':member_count,
        'threads':threads,
        'thread_count':thread_count,
        'event_count':event_count
       
    }

    if request.user.is_authenticated:
        return redirect('dashboard')


    return render(request, 'landing.html',context)

def userexists(request):
    return render(request, 'userexists.html')

def apply_view(request):
    # if the user clicked "submit application"
    if request.method =='POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        title = request.POST.get('title')
        company = request.POST.get('company')
        linkedin_url = request.POST.get('linkedin_url')

        # check if email alredy exists to prevent crashes
        if CustomUser.objects.filter(email=email).exists():
            messages.error(request,"An application with this email already exists.")
            return redirect('userexists')
        

        # Create New pending user in the database

        user = CustomUser.objects.create_user(
            username=email,
            email=email,
            first_name=first_name,
            last_name = last_name,
            title = title,
            company=company,
            linkedin_url = linkedin_url,
            is_active=False
        )

        # We don't set password yet because they aren't approved

        user.set_unusable_password()
        user.save()
        # Send them back to the landing page after applying
        # (Later, we can make a dedicated "Success" page)
        return redirect('landing_page')
    # If they are just visiting the page, show them the blank form
    return render(request, 'apply.html')

def login_view(request):

    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        # grab data from the form
        username = request.POST.get('username')
        password = request.POST.get('password')

        # django checks if these credentials match the data base

        user = authenticate(request, username=username, password=password)

        if user is not None:
            # The password is correct, log them in
            login(request,user)
            return redirect('dashboard')
        
        else:
            # The password is wrong , or user dosen't exists
            messages.error(request,"Invalid credentials or your account is pending approval.")
            return redirect('login')
    
    return render(request, 'login.html')


def logout_view(request):
    # this safely destroy the user's session
    logout(request)
    return redirect('landing_page',)


@login_required(login_url='login') # This kicks unauthorised 
def dashboard_view(request):
    # 1. Fetch all threads from the database, ordering by the newest first
    # 'select_related' makes the database query much faster!
    threads = Thread.objects.select_related('author','category').filter(replies__isnull=False).order_by('-created_at')[:5]
    

    #1a New discussion threads without any response

    threads_new = Thread.objects.select_related('author','category').filter(replies__isnull=True).order_by('-created_at')[:5]


    # fetch my discussion
    my_discussion_thred = Thread.objects.select_related('author','category').filter(Q(author=request.user) | Q(replies__author=request.user) ).order_by('-created_at')[:5]
    
    # 3. Package the data into a dictionary to send to html

    context={
        'threads':threads,
        'threads_new':threads_new,
        # 'upcoming_events':upcoming_events,
        'my_discussion_thred':my_discussion_thred,
        
      }

    
    return render(request,'dashboard.html',context)


@login_required(login_url='login') # This kicks unauthorised
def thread_detail_view(request,thread_id):
    # This securely fetches the thread, or throws a 404 error if it doesn't exist
    thread = get_object_or_404(Thread, id=thread_id)

    # If the user submitted a new reply, save it!
    if request.method == 'POST':
        reply_content = request.POST.get('content')
        if reply_content:
            Reply.objects.create(
                thread=thread,
                author=request.user,
                content=reply_content,
            )
            # Refresh the page so new comment appears instantly
            return redirect('thread_detail',thread_id=thread.id)
    
    # fetch all existing replies for this specific thread

    #replies = thread.replies.all().order_by('created_at')
    replies = thread.replies.prefetch_related('sub_replies','sub_replies__author').all()

    # members list
    # members = CustomUser.objects.filter(is_active=True, is_superuser=False).order_by('first_name')[:5]


    context = {
        'thread':thread,
        'replies':replies,
        # 'members':members,
    }

    return render(request,'thread_detail.html',context)


@login_required(login_url='login')
def add_subreply(request, reply_id):
    if request.method=="POST":
        # 1. find exact parent reply the use is responding to
        parent_reply=get_object_or_404(Reply,id=reply_id)

        # 2. grab the text they typed into the hidden form
        content = request.POST.get('content')

        # 3. Security check to ensure they didn't submit an empty box
        if content and content.strip():
            SubReply.objects.create(
                reply = parent_reply,
                author = request.user,
                content = content
            )
        # 4. Redirect back to the main thread.
        # because the parent_reply is linked to a thread, we can seamlessly grab the  thred id

        return redirect('thread_detail', thread_id=parent_reply.thread.id)

    # fallback safegaurd if someone tries to visit this url directly without submitting a form
    return redirect('dashboard')  



@login_required(login_url='login')
def create_thread_view(request):
    # Fetch categories so we can display them in the dropdown menu
    categories=Category.objects.all()

    if request.method == 'POST':
        title = request.POST.get('title')
        content = request.POST.get('content')
        category_id=request.POST.get('category')
    
    # Ensure all fields are filled out before saving
        if title and content and category_id:
            category = get_object_or_404(Category, id=category_id)

            # create new thread
            new_thread = Thread.objects.create(
                title=title,
                content=content,
                category=category,
                author=request.user
                
            )
            # Send the user directly to their newly created thread!
            return redirect('thread_detail',thread_id=new_thread.id)
    
    #if they are just loading the page, show them the blank form

    context ={
        'categories':categories
    }

    return render(request, 'create_thread.html', context)


@login_required(login_url='login')
def member_directory_view(request):
    # fetch all users who are marked as active, ordered by their first name
    # we exclude ther super user so the admin dosen't show up in member list

    members = CustomUser.objects.filter(is_active=True, is_superuser=False).order_by('first_name')
    categories = Category.objects.all()
    context = {
        'members':members,
        'categories':categories,
    }
    return render(request, 'members.html', context)


@login_required(login_url='login')
def category_list_view(request):
    #fetch all category

    categories = Category.objects.all().annotate(total_threads=Count('threads')).order_by('-total_threads')

    context = {
        'categories':categories
    }

    return render(request, 'topics.html',context)


@login_required(login_url='login')
def category_details(request, category_id):
    # 1 Grab the specific category (or show 404 if it didn't exist)
    category = get_object_or_404(Category, id=category_id)

    # 2 filtered thread data of selected category

    threads= Thread.objects.filter(category=category).order_by('-created_at')


    context= {
        'category':category,
        'threads':threads,
    }
    # 3 return data

    return render(request,'topic_details.html',context )


@login_required(login_url='login')
def profile_view(request):
    #get currently log-in cfo
    user = request.user

    # fetch there 5 most recent discussion threads

    recent_threds = Thread.objects.filter(author=user).order_by('-created_at')[:5]

    # fetch there 5 most recent replies, grabbing parent threads so we can link them

    recent_replies = Reply.objects.filter(author=user).select_related('thread').order_by('-created_at')[:5]

    context={
        'profile_user':user,
        'recent_threads':recent_threds,
        'recent_replies':recent_replies
    }
    return render(request, 'profile.html', context)



@login_required
def edit_profile(request):
    if request.method == 'POST':
        # request.Files is required to handle the image upload;

        form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect('profile')
        
    else:
        form = ProfileUpdateForm(instance=request.user)

    return render(request, 'edit_profile.html',{'form':form})


@login_required
def member_profile(request, user_id):
    # fetch the requested user
    viewed_user = get_object_or_404(CustomUser,id=user_id)


    # fetch there 5 most recent discussion threads

    recent_threds = Thread.objects.filter(author=viewed_user).order_by('-created_at')[:5]

    # fetch there 5 most recent replies, grabbing parent threads so we can link them

    recent_replies = Reply.objects.filter(author=viewed_user).select_related('thread').order_by('-created_at')[:5]

    context={
        'profile_user':viewed_user,
        'recent_threads':recent_threds,
        'recent_replies':recent_replies,
        'is_public_view': True, # A flag so the template knows NOT to show the "Edit Profile" button
    }
    return render(request, 'member_profile.html', context)



@login_required
def all_active_discussion_view(request):
    threads_all = Thread.objects.select_related('author','category').filter(replies__isnull=False).order_by('-created_at').distinct()
    
    # 2. Set up the Paginator to show 5 threads per page
    paginator = Paginator(threads_all, 5)

    # 3. Get the current page number from the URL (e.g., ?page=2)
    page_number = request.GET.get('page')

    # 4. Get the threads for that specific page
    threads = paginator.get_page(page_number)


    #1a New discussion threads without any response

    #threads_new = Thread.objects.select_related('author','category').filter(replies__isnull=True).order_by('-created_at')[:5]

    # 2. fetch all categories for sidebar

    # categories = Category.objects.all()

    # fetch events that happen after today, order by date (showing next 5)

    # upcoming_events = Event.objects.filter(date__gte=timezone.now()).order_by('date')[:5]

    # members list
    # members = CustomUser.objects.filter(is_active=True, is_superuser=False).order_by('first_name')[:5]

    # 3. Package the data into a dictionary to send to html

    
    

    context={
        'threads':threads,
        #'threads_new':threads_new,
        # 'categories':categories,
        #'upcoming_events':upcoming_events,
        # 'members':members,
        'page_number':page_number
    }

    
    return render(request,'all_active_discussion.html',context)






@login_required
def all_new_discussion_view(request):
    threads_all = Thread.objects.select_related('author','category').filter(replies__isnull=True).order_by('-created_at')

    # 2. Set up the Paginator to show 5 threads per page
    paginator = Paginator(threads_all, 5)

    # 3. Get the current page number from the URL (e.g., ?page=2)
    page_number = request.GET.get('page')

    # 4. Get the threads for that specific page
    threads = paginator.get_page(page_number)


    #1a New discussion threads without any response

    
    # 2. fetch all categories for sidebar

    # categories = Category.objects.all()

    # fetch events that happen after today, order by date (showing next 5)

    # upcoming_events = Event.objects.filter(date__gte=timezone.now()).order_by('date')[:5]

    # members list
    # members = CustomUser.objects.filter(is_active=True, is_superuser=False).order_by('first_name')[:5]

    # 3. Package the data into a dictionary to send to html

    
    

    context={
        'threads':threads,
        #'threads_new':threads_new,
        # 'categories':categories,
        #'upcoming_events':upcoming_events,
        # 'members':members,
        'page_number':page_number,
    }

    
    return render(request,'all_new_discussion.html',context)







@login_required
def my_discussion_view(request):
    threads_all = Thread.objects.select_related('author','category').filter(Q(author=request.user) | Q(replies__author=request.user) ).order_by('-created_at')
    
    # 2. Set up the Paginator to show 5 threads per page
    paginator = Paginator(threads_all, 5)

    # 3. Get the current page number from the URL (e.g., ?page=2)
    page_number = request.GET.get('page')

    # 4. Get the threads for that specific page
    threads = paginator.get_page(page_number)


    #1a New discussion threads without any response

    #threads_new = Thread.objects.select_related('author','category').filter(replies__isnull=True).order_by('-created_at')[:5]

    # 2. fetch all categories for sidebar

    # categories = Category.objects.all()

    # fetch events that happen after today, order by date (showing next 5)

    # upcoming_events = Event.objects.filter(date__gte=timezone.now()).order_by('date')[:5]

    # members list
    # members = CustomUser.objects.filter(is_active=True, is_superuser=False).order_by('first_name')[:5]

    # 3. Package the data into a dictionary to send to html

    
    

    context={
        'threads':threads,
        #'threads_new':threads_new,
        # 'categories':categories,
        #'upcoming_events':upcoming_events,
        # 'members':members,
        'page_number':page_number,
    }

    
    return render(request,'my_discussions.html',context)


@login_required
def mark_notification_read(request, notification_id):
    # find the specific notification and ensure it belongs to the loged in user
    notification = get_object_or_404(Notifications, id=notification_id, recipient=request.user)

    # mark it as read and save it!

    notification.is_read=True
    notification.save()

    # Redirect the user to the thread link we saved in the signal

    if notification.link:
        return redirect(notification.link)

    return redirect('dashboard') #fall back if there is no link

@login_required(login_url='login')
def global_search(request):
    #1. Grab the search word from the URL (e.g., ?q=finance)
    
    query = request.GET.get('q','')

    threads = []
    members = []
    categories = []

    if query:
        # 2. Search Discussions (Matches Title OR Content)

        threads = Thread.objects.filter(
            Q(title__icontains=query) | Q(content__icontains=query)
            ).distinct().order_by('-created_at')

        # 3. Search Members (Matches First Name, Last Name, or Company)
        members = User.objects.filter(
            Q(first_name__icontains=query) | 
            Q(last_name__icontains=query) | 
            Q(company__icontains=query)
        ).distinct()

        # 4. Search Categories (Matches Category Name)
        categories = Category.objects.filter(
            name__icontains=query
        ).distinct()


    context = {
            'query': query,
            'threads': threads,
            'members': members,
            'categories': categories,
    }


           # 5. Send all results to the template
    return render(request, 'search_results.html',context)

@login_required
def feedback(request):
    if request.method == 'POST':
        # Grab the data from the HTML form
        f_type = request.POST.get('feedback_type')
        title = request.POST.get('title')
        details = request.POST.get('details')
        
        # Save it to the database
        Feedback.objects.create(
            user=request.user,
            feedback_type=f_type,
            title=title,
            details=details
        )
        
        # Show a success message and redirect
        messages.success(request, "Thank you! Your feedback has been sent directly to the founding team.")
        return redirect('dashboard') # Or wherever you want them to go
        
   
    return render(request,'feedback_page.html')

@login_required
def invite_peer(request):
    return render(request, 'invite_a_peer_page.html')

