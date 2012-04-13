# encoding: utf-8
from django.views.decorators.csrf import csrf_protect, csrf_exempt
from django.shortcuts import get_object_or_404, redirect
from django.http import Http404
from django.conf import settings
from django.utils.translation import ugettext as _
from django.utils.html import strip_tags
from django.contrib import messages

from pytils.numeral import choose_plural




@csrf_protect
@render_to('cartds/cart.html')
def cart(request):
    cart = request.cart

    #only xhr allowed
    if not request.is_ajax(): return redirect('shop_list')

    try:
        delivery = Delivery.objects.filter(is_default=True)[0]
    except IndexError:
        delivery = None

    if delivery:
        form = OrderForm(initial={
            'delivery': delivery.pk
        })
    else:
        form = OrderForm()

    return {
        'cart': cart,
        'form': form,
        'delivery': delivery,
        'template': 'cartds/ajax.html'
    }

@render_to('cartds/goods.html')
def goods(request):
    cart = request.cart
    return {
        'cart': request.cart
    }

@ajax_request
def count(request):
    cart = request.cart
    count = len(cart)
    return {
        'count': count,
        'label': choose_plural(count, (u'товар', u'товара', u'товаров'))
    }

@csrf_protect
@ajax_request
def update(request):
    cart = request.cart
    
    if len(cart) == 0: return redirect('shop_list')
    
    if request.method == 'POST':
        try:
            product = Product.objects.get(pk=request.POST.get('product', None))

            try:
                quantity = int(request.POST.get('quantity'))
            except Exception:
                quantity = 1

            cart.remove(product, quantity)
            cart.save()
            context = {
                'cart': {
                    'products': cart.products(),
                    'price_total': cart.price_total(),
                    'count': len(cart)
                }
            }
        except Product.DoesNotExist, e:
            context = { 
                'errors': {
                    'product': str(e)
                } 
            }
        return context if request.is_ajax() else redirect('cart_order')
    else:
        raise Http404

@csrf_protect
@ajax_request
def add(request):
    if request.method == 'POST':
        form = ProductForm(request.POST or None)
        cart = request.cart

        if form.is_valid():
            product = form.cleaned_data['product']
            cart.append(product)
            cart.save()
            if request.is_ajax():
                return {
                    'cart': {
                        'products': cart.products(),
                        'price_total': cart.price_total(),
                        'count': len(cart)
                    }
                }
            else:
                return redirect('cart_order')
        else:
            return { 'errors': form.errors } if request.is_ajax() else redirect('cart_order')
    else:
        raise Http404


@csrf_protect
@ajax_request
def remove(request):
    cart = request.cart

    if request.method == 'POST':
        try:
            product = Product.objects.get(pk=request.POST.get('product', None))
            cart.remove(product)
            cart.save()
            context = {
                'cart': {
                    'products': cart.products(),
                    'price_total': cart.price_total(),
                    'count': len(cart)
                }
            }
        except Product.DoesNotExist, e:
            context = { 
                'errors': {
                    'product': str(e)
                } 
            }
        if request.is_ajax():
            return context
        else:
            return redirect('cart_order')
    else:
        raise Http404




@csrf_protect
@render_to('cartds/cart.html')
def order(request):
    cart = request.cart
    
    #if cart is empty, then say goodbye
    if len(cart) == 0: return redirect('shop_list')

    try:
        delivery = Delivery.objects.filter(is_default=True)[0]
    except IndexError:
        delivery = None

    context = {
        'cart': cart,
        'template': 'base.html'
    }
    if request.method == 'POST':
        form = OrderForm(request.POST, initial=request.POST)
        context.update(form=form)

        try:
            delivery = Delivery.objects.get(pk=int(form.data.get('delivery')))
        except Exception, e:
            pass

        if form.is_valid():
            email = form.cleaned_data.get('email')

            #if no user was found, then create it
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                user, created = User.objects.get_or_create(
                    username = email,
                    first_name = form.cleaned_data.get('first_name', ''),
                    last_name = form.cleaned_data.get('last_name', ''),
                    is_active = True,
                    email = form.cleaned_data.get('email')
                )

            try:
                profile = user.get_profile()
            except Profile.DoesNotExist:
                profile = Profile.objects.create(user=user)

            profile.phone = form.cleaned_data.get('phone')
            profile.save()

            order = Order.objects.create(
                user = user,
                comment = form.cleaned_data.get('comment', '')
            )
            order.save()

            #create delivery item with address or None
            delivery_item = OrderDelivery.objects.create(
                order = order,
                delivery = form.cleaned_data.get('delivery'),
                address = form.cleaned_data.get('address')
            )
            delivery_item.save()

            #add products to order
            for d in cart:
                order_item = OrderProduct.objects.create(
                    order = order,
                    product = d.product,
                    quantity = d.quantity
                )
                order_item.save()

            message_html = render_to_string('mail/user_order.html', {
                'cart': cart,
                'address': form.cleaned_data.get('address', ''),
                'phone': form.cleaned_data.get('phone'),
                'num': order.num
            })
            message_text = strip_tags(message_html)
            msg = EmailMultiAlternatives(_(u'Заказ на сайте deathstar.ru'), message_text, 'noreply@deathstar.ru', [user.email])
            msg.attach_alternative(message_html, 'text/html')
            msg.send()

            message_html = render_to_string('mail/new_order.html', {
                'cart': cart,
                'address': form.cleaned_data.get('address', ''),
                'phone': form.cleaned_data.get('phone'),
                'user': user,
                'comment': form.cleaned_data.get('comment', ''),
                'num': order.num
            })
            message_text = strip_tags(message_html)
            mail_managers(_(u'Новый заказ на сайте deathstar.ru'), message_text, html_message=message_html)
            mail_admins(_(u'Новый заказ на сайте deathstar.ru'), message_text, html_message=message_html)

            cart.empty()
            cart.save()

            messages.info(request, _(u"Ваш заказ оформлен. Письмо с инструкциями выслано на адрес %(email)s") % {'email': user.email})
            return redirect('shop_list')
    else:

        if delivery:
            form = OrderForm(initial={
                'delivery': delivery.pk
            })
        else:
            form = OrderForm()

    context.update(form=form, delivery=delivery)
    return context