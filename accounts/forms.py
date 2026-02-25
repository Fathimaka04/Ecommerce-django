from django import forms
from .models import account

class RegistrationFrom(forms.ModelForm):
    password=forms.CharField(widget=forms.PasswordInput(attrs={
        'placeholder':'Enter Password', # attrs means attributes html css etc..
        'class':'form-control',
    }))
    confirm_password=forms.CharField(widget=forms.PasswordInput(attrs={
        'placeholder':'Confirm Password' # attrs means attributes html css etc..
    }))
    class Meta:
        model= account
        fields=['first_name','last_name','phone_number','email','password']


    def clean(self):
        cleaned_data=super(RegistrationFrom,self).clean()
        password=cleaned_data.get('password')
        self.confirm_password=cleaned_data.get('confirm_password')


        if password!=self.confirm_password:
            raise forms.ValidationError(
                "Password does not match!")

    def __init__(self,*args,**kwargs):
        super(RegistrationFrom,self).__init__(*args,**kwargs) #keywordargs
        self.fields['first_name'].widget.attrs['placeholder']='Enter First Name'
        self.fields['last_name'].widget.attrs['placeholder']='Enter Last Name'
        self.fields['phone_number'].widget.attrs['placeholder']='Enter Phone Number '
        self.fields['email'].widget.attrs['placeholder']='Enter Email Address'
        for field in self.fields:
            self.fields[field].widget.attrs['class']='form-control'   # loop through all the fields anf give the attribute in first_name,last_name,etcc...


    