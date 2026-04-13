from django.contrib import admin
from .models import account,UserProfile
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
# Register your models here.
class accountadmin(UserAdmin):
    list_display=('email','first_name','last_name','username','last_login','date_join','is_active')
    list_display_links=('email','first_name','last_name')
    readonly_fields=('last_login','date_join')
    ordering=('-date_join',) # show the date in descending order and should be in a list or tuple
#    make password read only no edit option
    filter_horizontal=()
    list_filter=()
    fieldsets=()    
class UserProfileAdmin(admin.ModelAdmin):
    def thumbnail(self,object):
        if object.profile_picture:
            return format_html('<img src="{}" width="30" style="border-radius:50%;">',object.profile_picture.url)
        return "No Image"
    thumbnail.short_description='profile Picture'
    list_display=('thumbnail','user','city','state','country')

admin.site.register(account,accountadmin)
admin.site.register(UserProfile,UserProfileAdmin)
