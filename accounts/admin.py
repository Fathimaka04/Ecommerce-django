from django.contrib import admin
from .models import account
from django.contrib.auth.admin import UserAdmin
# Register your models here.
class accountadmin(UserAdmin):
    list_dispaly=('email','first_name','username','last_login','date_join','is_active')
    list_display_links=('email','first_name','last_name')
    readonly_fields=('last_login','date_join')
    ordering=('-date_join',) # show the date in descending order and should be in a list or tuple
#    make password read only no edit option
    filter_horizontal=()
    list_filter=()
    fieldsets=()    

admin.site.register(account,accountadmin)
