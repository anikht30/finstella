from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, get_user_model
from .models import CustomUser, Thread, Category,Reply,Event,SubReply,EventRegistration,Notifications,Feedback,PrivateNote
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .forms import ProfileUpdateForm
from django.core.paginator import Paginator
from django.db.models import Q
from django.db.models import Count
from django.urls import reverse
from django.core.mail import send_mail
from django.conf import settings
import string
from functools import wraps
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash



def subscription_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # 1. Always let superusers (you) through so you don't lock yourself out of your own app!
        if request.user.is_superuser:
            return view_func(request, *args, **kwargs)
            
        # 2. Check if the user has an active subscription
        if getattr(request.user, 'is_active_subscriber', False):
            return view_func(request, *args, **kwargs)
            
        # 3. If they are not a superuser and haven't paid, bounce them to checkout
        return redirect('checkout_view')
        
    return _wrapped_view


User = get_user_model()


@login_required
def checkout_view(request):
    # if the user is already active, send them straight to the dashboard
    if getattr(request.user,'is_active_subscriber',False):
        return redirect('dashboard')

    return render(request, 'checkout.html')


@login_required
def process_dummy_payment(request):
    if request.method == 'POST':
        # 1. We completely ignore the fake credit card data submitted in the form
        
        # 2. Activate the user's subscription status in your database
        # (Ensure you have a boolean field like 'has_active_subscription' on your User model)

        request.user.is_active_subscriber = True
        request.user.save()
        # 3. Trigger the success toast notification we built earlier!
        messages.success(request, "Payment successful! Welcome to the Finstella network.")

        # 4. Send them into the application
        return redirect('dashboard')
        
    return redirect('checkout_view')
    


@login_required
def events_page(request):
    today = timezone.now().date()
    # 1. Fetch only the approved events
    upcoming_events = Event.objects.filter(is_approved=True).filter(start_time__date=today)#.order_range(['start_time'])
    
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
        messages.success(request,"An application accepted successfully!")
        return redirect('login')
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
            # --- THE NEW SUBSCRIPTION CHECK ---
            # We use getattr() just in case the field doesn't exist on standard admin users
            if not getattr(user, 'has_active_subscription', False):
                # If they haven't paid, send them to the dummy payment gateway
                return redirect('checkout_view')
            return redirect('dashboard')
        
        else:
            # The password is wrong , or user dosen't exists
            messages.error(request,"Invalid credentials or your account is pending approval.")
            return redirect('login')
    
    # return render(request, 'login.html')
    return render(request, 'fellowship_login.html')


def logout_view(request):
    # this safely destroy the user's session
    logout(request)
    return redirect('landing_page',)


@login_required(login_url='login') # This kicks unauthorised
@subscription_required 
def dashboard_view(request):
    # 1. Fetch all threads from the database, ordering by the newest first
    # 'select_related' makes the database query much faster!
    threads = Thread.objects.select_related('author','category').filter(replies__isnull=False).order_by('-created_at').distinct()[:5]

    

    #1a New discussion threads without any response

    threads_new = Thread.objects.select_related('author','category').filter(replies__isnull=True).order_by('-created_at').distinct()[:5]


    # fetch my discussion
    my_discussion_thred = Thread.objects.select_related('author','category').filter(Q(author=request.user) | Q(replies__author=request.user) ).order_by('-created_at').distinct()[:5]
    
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
    replies = thread.replies.prefetch_related('sub_replies','sub_replies__author').all().order_by('-created_at')

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
             # 3. Add a success message to show the user
            messages.success(request, "Your query submitted successfully!")
            return redirect('thread_detail',thread_id=new_thread.id)
    
    #if they are just loading the page, show them the blank form

    context ={
        'categories':categories
    }

    return render(request, 'create_thread.html', context)


@login_required(login_url='login')
def member_directory_view(request):
    # get the selected letter from URL (defaults to 'All' if not set)
    selected_letter = request.GET.get('letter', 'All')
    
    # fetch all users who are marked as active, ordered by their first name
    # we exclude ther super user so the admin dosen't show up in member list


    members = CustomUser.objects.filter(is_active=True, is_superuser=False).order_by('first_name')

    # Filter if a specific letter (A-Z) is selected

    if selected_letter and selected_letter != 'All':
        members = members.filter(
            Q(first_name__istartswith=selected_letter) | 
            Q(last_name__istartswith=selected_letter)
        )

    # Generate list ['A', 'B', 'C', ..., 'Z']
    alphabet = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")#(string.ascii_letters)



    categories = Category.objects.all()
    context = {
        'members':members,
        'categories':categories,
        'alphabet':alphabet,
        'selected_letter':selected_letter,

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

    user_notifications = None
    if request.user.is_authenticated and request.user == user:
        user_notifications = Notifications.objects.filter(
            recipient=user
        ).order_by('-created_at')


    context={
        'profile_user':user,
        'recent_threads':recent_threds,
        'recent_replies':recent_replies,
        'user_notifications':user_notifications,
    }
    return render(request, 'profile.html', context)



@login_required
def edit_profile(request):
    if request.method == 'POST':
        
        # --- SCENARIO 1: USER IS UPDATING THEIR PASSWORD ---
        if 'change_password' in request.POST:
            # Re-instantiate the profile form just so it doesn't disappear from the page on a failed password attempt
            form = ProfileUpdateForm(instance=request.user) 
            password_form = PasswordChangeForm(request.user, request.POST)
            
            if password_form.is_valid():
                user = password_form.save()
                # CRITICAL: Keeps the user logged in after the password hash changes
                update_session_auth_hash(request, user)
                
                messages.success(request, "Your password was successfully updated!")
                return redirect('profile')
            else:
                messages.error(request, "Please correct the errors in the password form.")
                
        # --- SCENARIO 2: USER IS UPDATING THEIR PROFILE ---
        else:
            # request.FILES is required to handle the image upload
            form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user)
            password_form = PasswordChangeForm(request.user) # Keep password form blank
            
            if form.is_valid():
                form.save()
                messages.success(request, "Profile Updated Successfully!")
                return redirect('profile')
    
    # --- SCENARIO 3: USER IS JUST LOADING THE PAGE (GET REQUEST) ---
    else:
        form = ProfileUpdateForm(instance=request.user)
        password_form = PasswordChangeForm(request.user)

    # Pass both forms into your template
    return render(request, 'edit_profile.html', {
        'form': form,
        'password_form': password_form
    })

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
def click_notification_icon(request):
    if request.user.is_authenticated:
        # clear the red badge count without marking them as "read"
        Notifications.objects.filter(
            recipient = request.user,
            badge_cleared=False
        ).update(badge_cleared=True)
    # Redirect to profile page and append the tab instruction
    return redirect(f"{reverse('profile')}?tab=notifications")


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
    # 1. Handle the Form Submission (POST)
    if request.method == 'POST':
        peer_name = request.POST.get('peer_name', 'Colleague')
        peer_email = request.POST.get('peer_email')
        
        if peer_email:
            # Build the absolute URL for your registration page
            register_url = request.build_absolute_uri('/login/')
            
            subject = f"Invitation to join Finstella from {request.user.first_name} {request.user.last_name}"
            
            message = (
                f"Hello {peer_name},\n\n"
                f"{request.user.first_name} {request.user.last_name} has invited you to apply "
                f"for the exclusive Finstella network for finance leaders.\n\n"
                f"Click the link below to submit your application:\n"
                f"{register_url}?ref={request.user.username}\n\n"
                f"Best regards,\n"
                f"The Finstella Team"
            )
            
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [peer_email],
                fail_silently=False,
            )
            
            messages.success(request, f"Invitation successfully sent to {peer_name} at {peer_email}")
            
        # Redirect back to the same page so the form clears and the toast shows up
        return redirect('invite_peer') 

    # 2. Handle the Page Load (GET)
    # This is what was missing! It tells Django to render your HTML file.
    return render(request, 'invite_a_peer_page.html')


# The knowledge valut page
@login_required
def knowledge_vault(request):
     
     # This fetches ONLY the threads the logged-in user has saved
     saved_threads = request.user.saved_threads.all().order_by('-created_at')
     context = {
         'saved_threads':saved_threads
     }

     return render(request, 'knowledge_vault.html',context) 



# button login save / unsave 
@login_required
def toggle_bookmark(request, thread_id):
    thread = get_object_or_404(Thread, id=thread_id)

    # if its save already save it remove it (unsave)
    if request.user in thread.saved_by.all():
        thread.saved_by.remove(request.user)
        messages.success(request,"Removed from Knowledge Vault")

    # if they haven't saved it, add it (save)
    else:
        thread.saved_by.add(request.user)
        messages.success(request, "Saved to Knowledge Vault")

    # sends right back to the exact page user were just on

    return redirect(request.META.get('HTTP_REFERER', 'dashboard'))



@login_required
def private_workspace(request):
    # 1. Handle saving a new note
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        content = request.POST.get('content', '').strip()
        
        # Give it a default title if the user left it blank
        if not title and content:
            title = "Untitled Note"
            
        if content:
            PrivateNote.objects.create(
                user=request.user, 
                title=title, 
                content=content
            )
            messages.success(request, "Note saved to your private workspace.")
            return redirect('private_workspace')

    # 2. Fetch all existing notes ONLY for the logged-in user
    notes = PrivateNote.objects.filter(user=request.user)
    
    return render(request, 'private_workspace.html', {'notes': notes})

@login_required
def delete_note(request, note_id):
    # Ensure they can only delete their OWN notes
    note = get_object_or_404(PrivateNote, id=note_id, user=request.user)
    
    if request.method == 'POST':
        note.delete()
        messages.success(request, "Note deleted.")
        
    return redirect('private_workspace')

@login_required
def edit_note(request, note_id):
    # Ensure they can only edit their OWN notes
    note = get_object_or_404(PrivateNote, id=note_id, user=request.user)
    
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        content = request.POST.get('content', '').strip()
        
        if not title and content:
            title = "Untitled Note"
            
        if content:
            note.title = title
            note.content = content
            note.save()
            messages.success(request, "Note updated successfully.")
            return redirect('private_workspace')
            
    return render(request, 'edit_note.html', {'note': note})