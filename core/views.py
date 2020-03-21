import stripe
import json
import random
import string

from django.urls import reverse
from django.shortcuts import render, get_object_or_404, redirect
from django.core.exceptions import ObjectDoesNotExist
from django.views.generic import ListView, DetailView, View
from django.utils import timezone
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.conf import settings

from .models import Item, OrderItem, Order, Address, Payment, Coupon, Refund
from .forms import CheckoutForm, CouponForm, RefundForm

stripe_public_key = settings.STRIPE_PUBLIC_KEY
stripe.api_key = settings.STRIPE_SECRET_KEY

# Create Reference Code for Products
def create_ref_code():
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=20))

# Homepage View
class HomeView(ListView):
    model = Item
    template_name = 'home.html'
    paginate_by = 10

# Single Product View
class ItemDetailView(DetailView):
    model = Item
    template_name = 'products.html'

# Order Summary View
class OrderSummaryView(LoginRequiredMixin, View):
    def get(self, *args, **kwargs):
        try:
            # Get users orders than have not been ordered
            order = Order.objects.get(user=self.request.user, ordered=False)
            context = {
                'object': order
            }
            return render(self.request, 'order_summary.html', context)
        except ObjectDoesNotExist:
            messages.error(self.request, "You do not have an active order")
            return redirect('/')

def is_valid_form(values):
    valid = True
    for field in values:
        if field == '':
            valid = False
    return valid

# Checkout View
class CheckoutView(View):
    def get(self, *args, **kwargs):
        try:
            form = CheckoutForm()
            # Get users orders than have not been ordered
            order = Order.objects.get(
                user=self.request.user,
                ordered=False
            )

            context = {
                'form': form,
                'order': order,
                'couponform': CouponForm(),
                'DISPLAY_COUPON_FORM': True,
                'user': self.request.user
            }

            # Get default shipping address for user if it exists
            shipping_address_qs = Address.objects.filter(
                user=self.request.user, 
                address_type='S', 
                default=True
            )
            # Check if default shipping address for user does exist and parse to context
            if shipping_address_qs.exists():
                context.update({'default_shipping_address': shipping_address_qs[0]})

            # Get default billing address for user if it exists
            billing_address_qs = Address.objects.filter(
                user=self.request.user, 
                address_type='B', 
                default=True
            )
            # Check if default billing address for user does exist and parse to context
            if billing_address_qs.exists():
                context.update({'default_billing_address': billing_address_qs[0]})

            return render(self.request, 'checkout.html', context)

        except ObjectDoesNotExist:
            messages.info(self.request, "You do not have an active order")
            return redirect('core:checkout')

    def post(self, *args, **kwargs):
        form = CheckoutForm(self.request.POST or None)
        try:
            # Get users orders than have not been ordered
            order = Order.objects.get(user=self.request.user, ordered=False)

            if form.is_valid():
                 ### Shipping Address ###
                use_default_shipping = form.cleaned_data.get('use_default_shipping')

                # Check if user wants to use default shipping address
                if use_default_shipping:
                    print('using default shipping')

                    # Get default shipping address for user
                    address_qs = Address.objects.filter(
                        user=self.request.user, 
                        address_type='S', 
                        default=True
                    )

                    # Check if default shipping address does exist for user and assign to order
                    if address_qs.exists():
                        shipping_address = address_qs[0]
                        order.shipping_address = shipping_address
                        order.save()
                    else:
                        messages.info(self.request, 'No default shipping address available')
                        return redirect('core:checkout')
                
                # If the user does not want to use default shipping address
                else:
                    print('Not using default shipping')
                    # Get form data
                    shipping_first_name = form.cleaned_data.get('shipping_first_name')
                    shipping_last_name = form.cleaned_data.get('shipping_last_name')
                    shipping_address1 = form.cleaned_data.get('shipping_address')
                    shipping_address2 = form.cleaned_data.get('shipping_address2')
                    shipping_country = form.cleaned_data.get('shipping_country')
                    shipping_zip = form.cleaned_data.get('shipping_zip')

                    # Check against empty inputs
                    if is_valid_form([shipping_address1, shipping_country, shipping_zip,shipping_first_name, shipping_last_name]):
                        # Create shipping address object
                        shipping_address = Address(
                            user = self.request.user,
                            first_name = shipping_first_name,
                            last_name = shipping_last_name,
                            street_address = shipping_address1,
                            apartment_address = shipping_address2,
                            country = shipping_country,
                            zip = shipping_zip,
                            address_type = 'S'
                        )
                        shipping_address.save()

                        # Assign shipping address to order
                        order.shipping_address = shipping_address
                        order.save()

                        # If user wants to use address as default shipping address
                        set_default_shipping = form.cleaned_data.get('set_default_shipping')
                        if set_default_shipping:
                            shipping_address.default = True
                            shipping_address.save()
                    else:
                        messages.info(self.request, 'Please fill in the required shipping address fields')

                ### Billing Address ###
                use_default_billing = form.cleaned_data.get('use_default_billing')
                same_billing_address = form.cleaned_data.get('same_billing_address')

                # Check if billing address is the same as shipping address (from user input)
                if same_billing_address:
                    billing_address = shipping_address
                    billing_address.pk = None
                    billing_address.save()
                    billing_address.address_type = 'B'
                    billing_address.save()
                    # Assign billing address to order
                    order.billing_address = billing_address
                    order.save()

                # Check if user wants to use default billing address
                elif use_default_billing:
                    print('using default billing')

                    # Get default billing address for user
                    address_qs = Address.objects.filter(
                        user=self.request.user, 
                        address_type='B', 
                        default=True
                    )

                    # Check if default billing address does exist for user and assign to order
                    if address_qs.exists():
                        billing_address = address_qs[0]
                        order.billing_address = billing_address
                        order.save()
                    else:
                        messages.info(self.request, 'No default billing address available')
                        return redirect('core:checkout')
                
                # If the user does not want to use default billing address
                else:
                    print('User is entering new billing address')
                    # Get form data
                    billing_first_name = form.cleaned_data.get('billing_first_name')
                    billing_last_name = form.cleaned_data.get('billing_last_name')
                    billing_address1 = form.cleaned_data.get('billing_address')
                    billing_address2 = form.cleaned_data.get('billing_address2')
                    billing_country = form.cleaned_data.get('billing_country')
                    billing_zip = form.cleaned_data.get('billing_zip')

                    # Check against empty inputs
                    if is_valid_form([billing_address1, billing_country, billing_zip, billing_first_name, billing_last_name]):
                        # Create billing address object
                        billing_address = Address(
                            user = self.request.user,
                            first_name = billing_first_name,
                            last_name = billing_last_name,
                            street_address = billing_address1,
                            apartment_address = billing_address2,
                            country = billing_country,
                            zip = billing_zip,
                            address_type = 'B'
                        )
                        billing_address.save()

                        # Assign billing address to order
                        order.billing_address = billing_address
                        order.save()

                        # If user wants to use address as default billing address
                        set_default_billing = form.cleaned_data.get('set_default_billing')
                        if set_default_billing:
                            billing_address.default = True
                            billing_address.save()
                    else:
                        messages.info(self.request, 'Please fill in the required billing address fields')


                payment_option = form.cleaned_data.get('payment_option')
                
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
        user_name = f'{self.request.user.first_name} {self.request.user.last_name}'

        if order.billing_address:
            # Create payment intent
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
                'DISPLAY_COUPON_FORM': False,
                'user_name': user_name
            }

            return render(self.request, 'payment.html', context)

        else:
            messages.error(self.request, "You did not provide a billing address")
            return redirect('core:checkout')
    
class OrderConfirmedView(View):
    def post(self, *args, **kwargs):
        form = self.request.POST
        order = Order.objects.get(user=self.request.user, ordered=False)
        intent_id = form.get('intent_id')

        try:
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
            order.ref_code = create_ref_code()
            order.save()

            context = {
                'order': order
            }

            return render(self.request, 'order_confirmation.html', context)

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

       

class RequestRefundView(View):
    def get(self, *args, **kwargs):
        form = RefundForm()

        context = {
            'form': form
        }
        return render(self.request, 'request_refund.html', context)

    def post(self, *args, **kwargs):
        form = RefundForm(self.request.POST)
        if form.is_valid():
            ref_code = form.cleaned_data.get('ref_code')
            message = form.cleaned_data.get('message')
            email = form.cleaned_data.get('email')

            try:
                order = Order.objects.get(ref_code=ref_code)
                order.refund_requested = True
                order.save()
            
                refund = Refund()
                refund.order = order
                refund.reason = message
                refund.email = email
                refund.save()

                messages.info(self.request, 'Your request has been received.')
                return redirect('core:request-refund')

            except ObjectDoesNotExist:
                messages.info(self.request, 'This order does not exist')
                return redirect('core:request-refund')

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
