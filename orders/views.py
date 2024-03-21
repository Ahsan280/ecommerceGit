import datetime
import json

from django.core.mail import EmailMessage
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.template.loader import render_to_string


from store.models import Product
from .Forms import OrderForm
from carts.models import CartItem
from .models import Order, Payment, OrderProduct


# Create your views here.
def payments(request):
    body=json.loads(request.body)
    order=Order.objects.get(user=request.user, is_ordered=False, order_number=body['orderID'])
    # store transaction details inside payment model
    payment=Payment(
        user=request.user,
        payment_id=body['transactionID'],
        payment_method=body['payment_method'],
        amount_paid=order.order_total,
        status=body['status']
    )
    payment.save()
    order.payment=payment
    order.is_ordered=True
    order.save()

    # move the cartitems to OrderProduct model
    cart_items = CartItem.objects.filter(user=request.user)
    for item in cart_items:
        orderproduct=OrderProduct()
        orderproduct.order_id=order.id
        orderproduct.payment=payment
        orderproduct.user_id=request.user.id
        orderproduct.product_id=item.product.id
        orderproduct.quantity=item.quantity
        orderproduct.product_price=item.product.price
        orderproduct.ordered=True
        orderproduct.save()
        cart_item=CartItem.objects.get(id=item.id)
        product_variation = cart_item.variations.all()
        orderproduct=OrderProduct.objects.get(id=orderproduct.id)
        orderproduct.variations.set(product_variation)
        orderproduct.save()

        # reduce the quantity
        product=Product.objects.get(id=item.product_id)
        product.stock -= item.quantity
        product.save()

    # clear the cart
    CartItem.objects.filter(user=request.user).delete()
    # send order received email to customer

    # Send order number and transaction id back to SendData method via JsonResponse
    mail_subject = "Thank you for your order!"
    message = render_to_string('orders/order_receive_email.html', {
        'user': request.user,
        'order':order

    })
    to_email = request.user.email
    send_email = EmailMessage(mail_subject, message, to=[to_email])
    send_email.send()

    data={'order_number':order.order_number,
          'transID':payment.payment_id}

    return JsonResponse(data)
def order_complete(request):
    order_number=request.GET.get('order_number')
    transID=request.GET.get('payment_id')

    try:
        order=Order.objects.get(order_number=order_number, is_ordered=True)
        ordered_products=OrderProduct.objects.filter(order_id=order.id)
        subtotal=0
        for i in ordered_products:
            subtotal+=i.product_price*i.quantity

        payment=Payment.objects.get(payment_id=transID)
        return render(request, "orders/order_complete.html", context={'order': order,
                                                                      'ordered_products': ordered_products,
                                                                      'order_number':order.order_number,
                                                                      'transID':payment.payment_id,
                                                                      'payment':payment,
                                                                      'subtotal':subtotal,
                                                                      })
    except (Payment.DoesNotExist, Order.DoesNotExist):
        return redirect('home')



def place_order(request):
    current_user=request.user
    # if the cart count is less or equal to zero then redirect back to shop
    cart_items=CartItem.objects.filter(user=current_user)
    cart_count=cart_items.count()
    if cart_count<=0:
        return redirect("store")
    grand_total=0
    total=0
    tax=0
    quantity=0
    for cart_item in cart_items:
        total += cart_item.product.price * cart_item.quantity
        quantity+=cart_item.quantity
    tax = 0.02 * total
    grand_total=tax+total

    if request.method == "POST":
        form=OrderForm(request.POST)
        if form.is_valid():
            # store all the information inside the Order model (database)
            data=Order()
            data.first_name=form.cleaned_data['first_name']
            data.last_name=form.cleaned_data['last_name']
            data.email=form.cleaned_data['email']
            data.phone=form.cleaned_data['phone']
            data.address_line_1=form.cleaned_data['address_line_1']
            data.address_line_2=form.cleaned_data['address_line_2']
            data.country=form.cleaned_data['country']
            data.state=form.cleaned_data['state']
            data.city=form.cleaned_data['city']
            data.order_note=form.cleaned_data['order_note']
            data.order_total=grand_total
            data.tax=tax
            data.user=current_user
            data.ip=request.META.get('REMOTE_ADDR')
            data.save()

            # generate order number
            yr=int(datetime.datetime.today().strftime('%Y'))
            dt=int(datetime.datetime.today().strftime('%d'))
            mt=int(datetime.datetime.today().strftime('%m'))

            d=datetime.datetime(yr, mt, dt)
            current_date=d.strftime("%Y%m%d")
            order_number=current_date + str(data.id)
            data.order_number=order_number
            data.save()

            order=Order.objects.get(user=current_user, is_ordered=False, order_number=order_number)
            context={"order":order,
                     'cart_items':cart_items,
                     'total':total,
                     'grand_total':grand_total,
                     'tax':tax}


            return render(request, "orders/payments.html", context)
    else:
        return redirect("checkout")