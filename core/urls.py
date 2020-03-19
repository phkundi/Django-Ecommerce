from django.urls import path
from .views import (
    HomeView,
    ItemDetailView,
    OrderSummaryView,
    CheckoutView,
    PaymentView,
    add_to_cart,
    remove_from_cart,
    remove_single_item_from_cart,
    OrderConfirmedView,
    AddCouponView,
)

app_name = 'core'

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('order-summary/', OrderSummaryView.as_view(), name='order-summary'),
    path('checkout/', CheckoutView.as_view(), name='checkout'),
    path('order-confirmed/', OrderConfirmedView.as_view(), name='order-confirmed'),
    path('product/<slug>/', ItemDetailView.as_view(), name='product'),
    path('payment/<payment_option>', PaymentView.as_view(), name="payment"),
    path('add-to-cart/<slug>/', add_to_cart, name='add-to-cart'),
    path('add-coupon/', AddCouponView.as_view(), name='add-coupon'),
    path('remove-from-cart/<slug>/', remove_from_cart, name='remove-from-cart'),
    path('remove-single-item-from-cart/<slug>/',
         remove_single_item_from_cart, name='remove-single-item-from-cart'),
]
