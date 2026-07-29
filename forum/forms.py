from django import forms
from .models import CustomUser


class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['profile_picture','about','title','company','linkedin_url','mobileno','middle_name']
        