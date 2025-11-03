from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser, Account

class SignUpForm(UserCreationForm):
    # --- ADDED THIS FIELD ---
    terms = forms.BooleanField(
        required=True,
        label="I agree to the terms and conditions",
        error_messages={'required': 'You must agree to the terms.'}
    )
    # ------------------------

    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = ('username', 'email', 'first_name', 'last_name', 'address')

class TransferForm(forms.Form):
    from_account = forms.ModelChoiceField(
        queryset=Account.objects.none(), 
        label="From Account"
    )
    recipient = forms.CharField(label="Recipient (Account #, Email, or Username)", max_length=100)
    amount = forms.DecimalField(max_digits=10, decimal_places=2)
    note = forms.CharField(widget=forms.Textarea, required=False)

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super(TransferForm, self).__init__(*args, **kwargs)
        if user:
            self.fields['from_account'].queryset = Account.objects.filter(user=user)

class AccountCreationForm(forms.ModelForm):
    class Meta:
        model = Account
        fields = ['account_type', 'balance']

    def __init__(self, *args, **kwargs):
        # We remove the user argument as it's not used here, will be set in the view
        kwargs.pop('user', None)
        super(AccountCreationForm, self).__init__(*args, **kwargs)

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ('first_name', 'last_name', 'email', 'address')