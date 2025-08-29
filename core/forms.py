# core/forms.py
from django import forms
from django.core.exceptions import ValidationError
from .models import Account

class TransferForm(forms.Form):
    """
    Form for initiating money transfers between accounts.
    Includes validation for sufficient funds and account ownership.
    """
    def __init__(self, *args, **kwargs):
        # Get the user from kwargs and remove it before super().__init__()
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Only show accounts belonging to the current user
        if self.user:
            self.fields['from_account'].queryset = Account.objects.filter(user=self.user)

    recipient = forms.CharField(
        label="Recipient Account",
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Account number or email'
        }),
        help_text="Enter recipient's account number or registered email"
    )

    amount = forms.DecimalField(
        label="Amount",
        max_digits=15,
        decimal_places=2,
        min_value=0.01,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '0.00'
        })
    )

    from_account = forms.ModelChoiceField(
        label="From Account",
        queryset=Account.objects.none(),  # Will be set in __init__
        widget=forms.Select(attrs={
            'class': 'form-control'
        }),
        empty_label="Select your account"
    )

    note = forms.CharField(
        label="Note (Optional)",
        required=False,
        max_length=255,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': "What's this for?"
        })
    )

    def clean(self):
        cleaned_data = super().clean()
        from_account = cleaned_data.get('from_account')
        amount = cleaned_data.get('amount')

        # Check if the sender has sufficient funds
        if from_account and amount:
            if from_account.balance < amount:
                raise ValidationError(
                    "Insufficient funds in the selected account. "
                    f"Available balance: {from_account.balance}"
                )

        return cleaned_data

    def clean_recipient(self):
        recipient = self.cleaned_data['recipient']
        # Add additional validation for recipient format
        # Could check if it's a valid account number or email format
        return recipient


class AccountCreationForm(forms.ModelForm):
    """
    Form for creating new bank accounts.
    """
    class Meta:
        model = Account
        fields = ['account_type']
        widgets = {
            'account_type': forms.Select(attrs={
                'class': 'form-control'
            })
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

    def save(self, commit=True):
        account = super().save(commit=False)
        account.user = self.user
        # Generate account number (implementation depends on your requirements)
        account.account_number = self.generate_account_number()
        if commit:
            account.save()
        return account

    def generate_account_number(self):
        """
        Generate a unique account number.
        This is a simple implementation - adjust according to your requirements.
        """
        import random
        while True:
            number = f"{self.user.id:04d}{random.randint(1000, 9999)}"
            if not Account.objects.filter(account_number=number).exists():
                return number


class UserProfileForm(forms.ModelForm):
    """
    Form for updating user profile information.
    """
    class Meta:
        from .models import CustomUser
        model = CustomUser
        fields = ['first_name', 'last_name', 'email', 'phone_number', 'address']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make email required (it's optional by default in AbstractUser)
        self.fields['email'].required = True
