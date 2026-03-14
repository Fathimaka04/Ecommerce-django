


from django.urls import path
from .import views


urlpatterns = [
   
    path('place_order/',views.place_order,name='place_order'),
    path('payments/',views.payments,name='payments'),
    path('fake_payment/<str:order_number>/', views.fake_payment, name='fake_payment'),
    path('bill/<str:order_number>/', views.order_bill, name='order_bill'),
    
]                                            
