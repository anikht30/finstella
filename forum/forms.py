from django import forms
from .models import CustomUser


class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['profile_picture','about','title','company',
                  'linkedin_url','mobileno','middle_name','first_name',
                  'last_name','professional_qualification', 'city', 'state', 'country',
                  'show_email', 'show_mobile_no', 'country_code']
        