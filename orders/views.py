
import datetime
import uuid

from django.shortcuts import render,redirect,get_object_or_404

from carts.models import CartItem
from store.models import Product
from .forms import OrderForm
from .models import Order,OrderProduct,Payment
from django.contrib.auth.decorators import login_required
from django.core.mail import EmailMessage
from django.template.loader import render_to_string


def payments(request):
    return render(request,'orders/payments.html')


def place_order(request,total=0,quantity=0):
    current_user=request.user
    cart_items=CartItem.objects.filter(user=current_user)
    cart_count=cart_items.count()
    # if the cart count is less than or equal to 0 redirect back to shop

    if cart_count <=0:
        return redirect('store')
    
    grand_total=0
    tax=0

    for cart_item in cart_items:
        total += (cart_item.product.price*cart_item.quantity)
        quantity += cart_item.quantity

    tax = (2*total)/100
    grand_total = total+tax
    
    if request.method == 'POST':
        form=OrderForm(request.POST)
        if form.is_valid():
            # store all the billing information inside Order table
            data=Order()
            data.user=current_user
            data.first_name=form.cleaned_data['first_name']
            data.last_name=form.cleaned_data['last_name']
            data.phone=form.cleaned_data['phone']
            data.email=form.cleaned_data['email']
            data.address_line_1=form.cleaned_data['address_line_1']
            data.address_line_2=form.cleaned_data['address_line_2']
            data.country=form.cleaned_data['country']
            data.state=form.cleaned_data['state']
            data.city=form.cleaned_data['city']
            data.order_note=form.cleaned_data['order_note']
            data.order_total=grand_total
            data.tax=tax
            data.ip=request.META.get('REMOTE_ADDR')
            data.save()
            # generate order number
            yr=int(datetime.date.today().strftime('%Y'))
            dt=int(datetime.date.today().strftime('%d'))
            mt=int(datetime.date.today().strftime('%m'))
            d=datetime.date(yr,mt,dt)
            current_date=d.strftime("%Y%m%d") #20260310
            order_number=current_date +str(data.id) #concatenate id and date
            data.order_number=order_number
            data.save()

            order=Order.objects.get(user=current_user,is_ordered=False,order_number=order_number)
            context={
                'order':order,
                'cart_items':cart_items,
                'total':total,
                'tax': tax,
                'grand_total': grand_total,



            }
            return render(request,'orders/payments.html',context)
        
        else:
            return redirect('checkout')
        

@login_required(login_url='login')
def fake_payment(request, order_number):
    current_user = request.user
    order = get_object_or_404(Order, order_number=order_number, user=current_user, is_ordered=False)

    # Get cart items for order summary display
    cart_items = CartItem.objects.filter(user=current_user)

    if request.method == 'POST':
        card_number = request.POST.get('card_number', '').replace(' ', '')
        card_name = request.POST.get('card_name', '')
        expiry = request.POST.get('expiry', '')
        cvv = request.POST.get('cvv', '')

        # Basic validation
        errors = []
        if len(card_number) < 13 or len(card_number) > 19:
            errors.append('Invalid card number.')
        if not card_name.strip():
            errors.append('Cardholder name is required.')
        if len(expiry) != 5 or '/' not in expiry:
            errors.append('Invalid expiry date (use MM/YY).')
        if len(cvv) < 3 or len(cvv) > 4:
            errors.append('Invalid CVV.')

        if errors:
            context = {
                'order': order,
                'cart_items': cart_items,
                'total': float(order.order_total) - float(order.tax),
                'tax': order.tax,
                'grand_total': order.order_total,
                'errors': errors,
            }
            return render(request, 'orders/fake_payment.html', context)

        # Create fake Payment record
        fake_payment_id = 'FAKE-' + uuid.uuid4().hex[:12].upper()
        payment = Payment(
            user=current_user,
            payment_id=fake_payment_id,
            payment_method='Fake Credit Card',
            amount_paid=str(order.order_total),
            status='Completed',
        )
        payment.save()

        # Update order
        order.payment = payment
        order.is_ordered = True
        order.status = 'Accepted'
        order.save()

        # move  cart-items  to orderproduct
        for cart_item in cart_items:
            order_product = OrderProduct()
            order_product.order = order
            order_product.payment = payment
            order_product.user = current_user
            order_product.product = cart_item.product
            order_product.quantity = cart_item.quantity
            order_product.product_price = cart_item.product.price
            order_product.ordered = True
            order_product.save()

            variations=cart_item.variations.all()             #adding the variation 
            if variations.exists():
                order_product.variations.set(variations)


            #reducing  the  quantity of the sold product
            product = Product.objects.get(id=cart_item.product.id)
            product.stock -=cart_item.quantity
            product.save()

        # Clear the cart
        cart_items.delete()


        #Send order recieved email to customer

        mail_subject='Thank you for your order'
        message=render_to_string('orders/order_recieved_email.html',{
                 'user': request.user,
                 'order':order,
            })
        to_email=request.user.email
        send_email=EmailMessage(mail_subject,message,to=[to_email])
        send_email.send()

        return redirect('order_bill', order_number=order.order_number)

    # GET request — show the payment form
    total = float(order.order_total) - float(order.tax)
    context = {
        'order': order,
        'cart_items': cart_items,
        'total': total,
        'tax': order.tax,
        'grand_total': order.order_total,
    }
    return render(request, 'orders/fake_payment.html', context)


@login_required(login_url='login')
def order_bill(request, order_number):
    current_user = request.user
    order = get_object_or_404(Order, order_number=order_number, user=current_user, is_ordered=True)
    order_products = OrderProduct.objects.filter(order=order)
    payment = order.payment

    subtotal = 0
    for op in order_products:
        subtotal += op.product_price * op.quantity

    context = {
        'order': order,
        'order_products': order_products,
        'payment': payment,
        'subtotal': subtotal,
    }
    return render(request, 'orders/bill.html', context)

