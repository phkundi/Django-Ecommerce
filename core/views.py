import stripe
import json

from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.core.exceptions import ObjectDoesNotExist
from django.views.generic import ListView, DetailView, View
from django.utils import timezone
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.conf import settings

from .models import Item, OrderItem, Order, BillingAddress, Payment, Coupon
from .forms import CheckoutForm, CouponForm

stripe_public_key = settings.STRIPE_PUBLIC_KEY
stripe.api_key = settings.STRIPE_SECRET_KEY

def products(request):
    context = {
        'items': Item.objects.all()
    }
    return render(request, 'products.html', context)


def checkout(request):
    return render(request, 'checkout.html')


class HomeView(ListView):
    model = Item
    template_name = 'home.html'
    paginate_by = 10

class ItemDetailView(DetailView):
    model = Item
    template_name = 'products.html'

class OrderSummaryView(LoginRequiredMixin, View):
    def get(self, *args, **kwargs):
        try:
            order = Order.objects.get(user=self.request.user, ordered=False)
            context = {
                'object': order
            }
            return render(self.request, 'order_summary.html', context)
        except ObjectDoesNotExist:
            messages.error(self.request, "You do not have an active order")
            return redirect('/')

class CheckoutView(View):
    def get(self, *args, **kwargs):
        try:
            form = CheckoutForm()
            order = Order.objects.get(
               user=self.request.user,
                ordered=False
            )

            context = {
                'form': form,
                'order': order,
                'couponform': CouponForm(),
                'DISPLAY_COUPON_FORM': True
            }

            return render(self.request, 'checkout.html', context)

        except ObjectDoesNotExist:
            messages.info(self.request, "You do not have an active order")
            return redirect('core:checkout')

    def post(self, *args, **kwargs):
        form = CheckoutForm(self.request.POST or None)
        try:
            order = Order.objects.get(user=self.request.user, ordered=False)

            if form.is_valid():
                street_address = form.cleaned_data.get('street_address')
                apartment_address = form.cleaned_data.get('apartment_address')
                country = form.cleaned_data.get('country')
                zip = form.cleaned_data.get('zip')
                # TODO: Add these fields
                # same_shipping_address = form.cleaned_data.get('same_shipping_address')
                # save_info = form.cleaned_data.get('save_info')
                payment_option = form.cleaned_data.get('payment_option')
                billing_address = BillingAddress(
                    user = self.request.user,
                    street_address = street_address,
                    apartment_address = apartment_address,
                    country = country,
                    zip = zip
                )
                billing_address.save()
                order.billing_address = billing_address
                order.save()
                
                if payment_option == 'S':
                    return redirect('core:payment', payment_option='stripe')
                elif payment_option == 'P':
                    return redirect('core:payment', payment_option='paypal')
                else:
                    messages.warning(self.request, "Invalid Payment option selected")

            messages.warning(self.request, 'Failed checkout')
            return redirect('core:checkout')

        except ObjectDoesNotExist:
            messages.error(self.request, "You do not have an active order")
            return redirect('core:order-summary')
        
class PaymentView(View):
    def get(self, *args, **kwargs):
        order = Order.objects.get(user=self.request.user, ordered=False)
        amount = int(order.get_total() * 100)

        if order.billing_address:
            intent = stripe.PaymentIntent.create(
                amount=amount,
                currency='eur',
                # Verify your integration in this guide by including this parameter
                metadata={'integration_check': 'accept_a_payment'},
            )
            
            context = {
                'client_secret': intent.client_secret,
                'stripe_public_key': stripe_public_key,
                'intent_id': intent.id,
                'order': order,
                'DISPLAY_COUPON_FORM': False
            }

            return render(self.request, 'payment.html', context)
        else:
            messages.error(self.request, "You do not provided a billing address")
            return redirect('core:checkout')

    #TODO: Move to order confirmed page
    def post(self, *args, **kwargs):
        
        return redirect('/')

class OrderConfirmedView(View):
    def post(self, *args, **kwargs):
        order = Order.objects.get(user=self.request.user, ordered=False)
        intent_id = self.request.POST.get('intent_id')

        context = {
            'order': order
        }

        try:
            # Use Stripe's library to make requests...
            pass
            pass
        except stripe.error.CardError as e:
            # Since it's a decline, stripe.error.CardError will be caught
            messages.error(self.request, f"{e.error.message}")
            return redirect('/')
        except stripe.error.RateLimitError as e:
            # Too many requests made to the API too quickly
            messages.error(self.request, f"{e.error.message}")
            return redirect('/')
        except stripe.error.InvalidRequestError as e:
            # Invalid parameters were supplied to Stripe's API
            messages.error(self.request, f"{e.error.message}")
            return redirect('/')
        except stripe.error.AuthenticationError as e:
            # Authentication with Stripe's API failed
            # (maybe you changed API keys recently)
            messages.error(self.request, f"{e.error.message}")
            return redirect('/')
        except stripe.error.APIConnectionError as e:
            # Network communication with Stripe failed
            messages.error(self.request, f"{e.error.message}")
            return redirect('/')
        except stripe.error.StripeError as e:
            # Display a very generic error to the user, and maybe send
            # yourself an email
            messages.error(self.request, f"{e.error.message}")
            return redirect('/')
        except Exception as e:
            # Send email to ourselves
            messages.error(self.request, "A serious error has occured, we have been notified and will look into it")
            pass

         # create the payment
        payment = Payment()
        payment.stripe_charge_id = intent_id
        payment.user = self.request.user
        payment.amount = order.get_total()
        payment.save()

        #assign payment to order
        order_items = order.items.all()
        order_items.update(ordered=True)
        for item in order_items:
            item.save()

        order.ordered = True
        order.payment = payment
        order.save()
    
        return render(self.request, 'order_confirmation.html', context)

def add_to_cart(request, slug):
    item = get_object_or_404(Item, slug=slug)

    order_item, created = OrderItem.objects.get_or_create(
        item=item,
        user=request.user,
        ordered=False
    )

    order_qs = Order.objects.filter(
        user=request.user,
        ordered=False
    )

    if order_qs.exists():
        order = order_qs[0]
        # check if order item is in the order
        if order.items.filter(item__slug=item.slug).exists():
            order_item.quantity += 1
            order_item.save()
            messages.info(request, "Item quantity updated")
            return redirect('core:order-summary')
        else:
            messages.info(request, "This item was added to your cart")
            order.items.add(order_item)
            return redirect('core:order-summary')
    else:
        ordered_date = timezone.now()
        order = Order.objects.create(
            user=request.user,
            ordered_date=ordered_date,
        )
        order.items.add(order_item)
        messages.info(request, "This item was added to your cart")
        return redirect("core:order-summary")

@login_required
def remove_from_cart(request, slug):
    item = get_object_or_404(Item, slug=slug)
    order_qs = Order.objects.filter(
        user=request.user,
        ordered=False
    )

    if order_qs.exists():
        order = order_qs[0]
        # check if order item is in the order
        if order.items.filter(item__slug=item.slug).exists():
            order_item = OrderItem.objects.filter(
                item=item,
                user=request.user,
                ordered=False
            )[0]
            order.items.remove(order_item)
            order_item.delete()
            messages.info(request, "This item was removed from your cart")
            return redirect("core:order-summary")

        else:
            messages.info(request, "This item was not in your cart")
            return redirect('core:product', slug=slug)

    else:
        messages.info(request, "There is nothing in your cart")
        return redirect('core:product', slug=slug)


@login_required
def remove_single_item_from_cart(request, slug):
    item = get_object_or_404(Item, slug=slug)
    order_qs = Order.objects.filter(
        user=request.user,
        ordered=False
    )

    if order_qs.exists():
        order = order_qs[0]
        # check if order item is in the order
        if order.items.filter(item__slug=item.slug).exists():
            order_item = OrderItem.objects.filter(
                item=item,
                user=request.user,
                ordered=False
            )[0]
            if order_item.quantity > 1:
                order_item.quantity -= 1
                order_item.save()
            else:
                order.items.remove(order_item)
                order_item.save()
            messages.info(request, "This items quantity was updated")
            return redirect("core:order-summary")

        else:
            messages.info(request, "This item was not in your cart")
            return redirect('core:product', slug=slug)

    else:
        messages.info(request, "There is nothing in your cart")
        return redirect('core:product', slug=slug)

def get_coupon(request, code):
    try:
       coupon = Coupon.objects.get(code=code)
       return coupon
        
    except ObjectDoesNotExist:
        messages.info(request, "This coupon does not exist")

class AddCouponView(View):
    def post(self, *args, **kwargs):
        form = CouponForm(self.request.POST or None)
        if form.is_valid():
            try:
                code = form.cleaned_data.get('code')
                order = Order.objects.get(
                    user=self.request.user,
                    ordered=False
                )
                order.coupon = get_coupon(self.request, code)
                order.save()
                messages.success(self.request, 'Successfully added coupon')
                return redirect('core:checkout')
                
            except ObjectDoesNotExist:
                messages.info(self.request, "You do not have an active order")
                return redirect('core:checkout')
        return None
