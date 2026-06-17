from django import forms
from .models import JobDeveloper

class DeveloperForm(forms.ModelForm):
    class Meta:
        model = JobDeveloper
        fields = ['developer_name', 'department', 'team']
        labels = {
            'department': 'Select Department'
        }
        widgets = {
            'developer_name': forms.TextInput(attrs={
                'class': 'form-control'
            }),
            'department': forms.Select(attrs={
                'class': 'form-select'
            }),
            'team': forms.TextInput(attrs={
                'class': 'form-control'
            }),
        }
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.fields['department'].empty_label = 'Select Department'
