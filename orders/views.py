import datetime
import uuid
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.db import transaction

from carts.models import CartItem
from store.models import Product
from .forms import OrderForm
from .models import Order, OrderProduct, Payment

def payments(request):
    return render(request, 'orders/payments.html')

@login_required(login_url='login')
def place_order(request, total=0, quantity=0):
    current_user = request.user
    cart_items = CartItem.objects.filter(user=current_user)
    cart_count = cart_items.count()

    if cart_count <= 0:
        return redirect('store')
    
    grand_total = 0
    tax = 0

    for cart_item in cart_items:
        total += (cart_item.product.price * cart_item.quantity)
        quantity += cart_item.quantity

    tax = (2 * total) / 100
    grand_total = total + tax
    
    if request.method == 'POST':
        form = OrderForm(request.POST)
        if form.is_valid():
            # Store billing info
            data = Order()
            data.user = current_user
            data.first_name = form.cleaned_data['first_name']
            data.last_name = form.cleaned_data['last_name']
            data.phone = form.cleaned_data['phone']
            data.email = form.cleaned_data['email']
            data.address_line_1 = form.cleaned_data['address_line_1']
            data.address_line_2 = form.cleaned_data['address_line_2']
            data.country = form.cleaned_data['country']
            data.state = form.cleaned_data['state']
            data.city = form.cleaned_data['city']
            data.order_note = form.cleaned_data['order_note']
            data.order_total = grand_total
            data.tax = tax
            data.ip = request.META.get('REMOTE_ADDR')
            data.save()

            # Generate order number
            yr = int(datetime.date.today().strftime('%Y'))
            dt = int(datetime.date.today().strftime('%d'))
            mt = int(datetime.date.today().strftime('%m'))
            current_date = datetime.date(yr, mt, dt).strftime("%Y%m%d")
            order_number = current_date + str(data.id)
            data.order_number = order_number
            data.save()

            return redirect('fake_payment', order_number=data.order_number)
        else:
            return redirect('checkout')
    
    return redirect('checkout')

@login_required(login_url='login')
def fake_payment(request, order_number):
    current_user = request.user
    # FIX: Remove is_ordered=False from the 404 check so the view can still load if refreshed
    order = get_object_or_404(Order, order_number=order_number, user=current_user)

    # If the order is already paid for, don't show the payment page again
    if order.is_ordered:
        return redirect('order_bill', order_number=order.order_number)

    cart_items = CartItem.objects.filter(user=current_user)

    if request.method == 'POST':
        card_number = request.POST.get('card_number', '').replace(' ', '')
        card_name = request.POST.get('card_name', '')
        expiry = request.POST.get('expiry', '')
        cvv = request.POST.get('cvv', '')

        errors = []
        if len(card_number) < 13: errors.append('Invalid card number.')
        if not card_name.strip(): errors.append('Cardholder name is required.')
        if '/' not in expiry: errors.append('Invalid expiry (MM/YY).')
        if len(cvv) < 3: errors.append('Invalid CVV.')

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

        # Transactional block ensures either everything saves or nothing saves
        with transaction.atomic():
            # 1. Create Payment record
            payment = Payment(
                user=current_user,
                payment_id='FAKE-' + uuid.uuid4().hex[:12].upper(),
                payment_method='Fake Credit Card',
                amount_paid=str(order.order_total),
                status='Completed',
            )
            payment.save()

            # 2. Update Order
            order.payment = payment
            order.is_ordered = True
            order.status = 'Accepted'
            order.save()

            # 3. Move Cart items to OrderProduct
            for item in cart_items:
                order_product = OrderProduct.objects.create(
                    order=order,
                    payment=payment,
                    user=current_user,
                    product=item.product,
                    quantity=item.quantity,
                    product_price=item.product.price,
                    ordered=True
                )
                # Handle variations
                if item.variations.exists():
                    order_product.variations.set(item.variations.all())

                # 4. Reduce Stock
                product = item.product
                product.stock -= item.quantity
                product.save()

            # 5. Clear Cart
            cart_items.delete()

        # 6. Send Email
        try:
            mail_subject = 'Thank you for your order'
            message = render_to_string('orders/order_recieved_email.html', {
                'user': current_user,
                'order': order,
            })
            to_email = current_user.email
            send_email = EmailMessage(mail_subject, message, to=[to_email])
            send_email.send()
        except Exception:
            pass # Fail silently if email server is not configured

        return redirect('order_bill', order_number=order.order_number)

    # GET request logic
    subtotal = float(order.order_total) - float(order.tax)
    context = {
        'order': order,
        'cart_items': cart_items,
        'total': subtotal,
        'tax': order.tax,
        'grand_total': order.order_total,
    }
    return render(request, 'orders/fake_payment.html', context)

@login_required(login_url='login')
def order_bill(request, order_number):
    current_user = request.user
    # Note: filter by is_ordered=True because this is a bill for a completed order
    order = get_object_or_404(Order, order_number=order_number, user=current_user, is_ordered=True)
    order_products = OrderProduct.objects.filter(order=order)

    subtotal = sum(op.product_price * op.quantity for op in order_products)

    context = {
        'order': order,
        'order_products': order_products,
        'payment': order.payment,
        'subtotal': subtotal,
    }
    return render(request, 'orders/bill.html', context)