from django import forms
from django_countries.fields import CountryField
from django_countries.widgets import CountrySelectWidget
from allauth.account.forms import SignupForm

PAYMENT_CHOICES = (
    ('S', 'Stripe'),
    ('P', 'PayPal')
)

class CheckoutForm(forms.Form):
    shipping_first_name = forms.CharField(required=False)
    shipping_last_name = forms.CharField(required=False)
    shipping_address = forms.CharField(required=False)
    shipping_address2 = forms.CharField(required=False)
    shipping_country = CountryField(blank_label='Select country').formfield(
        required=False,
        widget=CountrySelectWidget(attrs={
            'class': 'custom-select d-block w-100',
        }))
    shipping_zip = forms.CharField(required=False)
    
    billing_first_name = forms.CharField(required=False)
    billing_last_name = forms.CharField(required=False)
    billing_address = forms.CharField(required=False)
    billing_address2 = forms.CharField(required=False)
    billing_country = CountryField(blank_label='Select country').formfield(
        required=False,
        widget=CountrySelectWidget(attrs={
            'class': 'custom-select d-block w-100',
        }))
    billing_zip = forms.CharField(required=False)

    same_billing_address = forms.BooleanField(widget=forms.CheckboxInput, required=False)
    set_default_shipping = forms.BooleanField(widget=forms.CheckboxInput, required=False)
    use_default_shipping = forms.BooleanField(widget=forms.CheckboxInput, required=False)
    set_default_billing = forms.BooleanField(widget=forms.CheckboxInput, required=False)
    use_default_billing = forms.BooleanField(widget=forms.CheckboxInput, required=False)
    payment_option = forms.ChoiceField(widget=forms.RadioSelect, choices=PAYMENT_CHOICES)

class CouponForm(forms.Form):
    code = forms.CharField(widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Promo Code',
        'aria-label': 'Recipient\'s username',
        'aria-desribedby': 'basic-addon2'
    }))

class RefundForm(forms.Form):
    ref_code = forms.CharField()
    message = forms.CharField(widget=forms.Textarea(attrs={
        'rows': 4
    }))
    email = forms.EmailField()

class CustomSignupForm(SignupForm):
    first_name = forms.CharField(max_length=30, label='First Name', widget=forms.TextInput(attrs={
        'placeholder': 'First Name'
    }))
    last_name = forms.CharField(max_length=30, label='Last Name', widget=forms.TextInput(attrs={
        'placeholder': 'Last Name'
    }))

    def signup(self, request, user):
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.save()
        return user