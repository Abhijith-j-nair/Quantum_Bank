# core/views.py
import uuid
from django.http import HttpResponse
import qrcode
from io import BytesIO
# --- THIS IS THE FIX ---
from django.urls import reverse
# ------------------------
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.core.paginator import Paginator
from django.utils import timezone
from datetime import datetime
from .forms import TransferForm, AccountCreationForm, UserProfileForm, SignUpForm
from .models import Account, Transaction, CustomUser
from .serializers import TransactionSerializer
from rest_framework.decorators import api_view
from rest_framework.response import Response


def generate_account_number():
    return str(uuid.uuid4().int)[:10]


def signup_view(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            Account.objects.create(
                user=user,
                account_type='Checking',
                balance=0.00,
                account_number=generate_account_number()
            )
            login(request, user)
            return redirect('home')
    else:
        form = SignUpForm()
    return render(request, 'registration/signup.html', {'form': form})


@login_required
def create_account_view(request):
    if request.method == 'POST':
        form = AccountCreationForm(request.POST)
        if form.is_valid():
            account = form.save(commit=False)
            account.user = request.user
            account.account_number = generate_account_number()
            account.save()
            messages.success(request, f"New {account.account_type} account created!")
            return redirect('accounts')
    else:
        form = AccountCreationForm()
    return render(request, 'core/create_account.html', {'form': form})


@login_required
def dashboard_view(request):
    user_accounts = Account.objects.filter(user=request.user)
    total_balance = sum(account.balance for account in user_accounts)
    checking_account = user_accounts.filter(account_type__iexact='Checking').first()
    savings_account = user_accounts.filter(account_type__iexact='Savings').first()
    checking_balance = checking_account.balance if checking_account else 0.00
    savings_balance = savings_account.balance if savings_account else 0.00
    recent_transactions = Transaction.objects.filter(
        Q(sender_account__user=request.user) | Q(receiver_account__user=request.user)
    ).order_by('-timestamp')[:5]

    context = {
        'user_accounts': user_accounts,
        'total_balance': total_balance,
        'checking_account': checking_account,
        'savings_account': savings_account,
        'checking_balance': checking_balance,
        'savings_balance': savings_balance,
        'recent_transactions': recent_transactions,
    }
    return render(request, 'core/dashboard.html', context)


@login_required
@transaction.atomic
def transfer_view(request):
    # ... (This view remains the same)
    pass


@login_required
def pay_me_view(request, account_number):
    recipient_account = get_object_or_404(Account, account_number=account_number)
    initial_data = {'recipient': recipient_account.account_number}
    form = TransferForm(user=request.user, initial=initial_data)
    return render(request, 'core/transfer.html', {'form': form, 'recipient_account': recipient_account})


@login_required
def transaction_list_view(request):
    # ... (This view remains the same)
    pass


@login_required
def account_detail_view(request, account_id):
    # ... (This view remains the same)
    pass


@api_view(['GET'])
@login_required
def api_transaction_detail(request, transaction_id):
    # ... (This view remains the same)
    pass


@login_required
def qr_code_view(request, account_id):
    account = get_object_or_404(Account, id=account_id, user=request.user)
    pay_me_url = request.build_absolute_uri(
        reverse('pay_me', args=[account.account_number])
    )
    data = pay_me_url
    qr_image = qrcode.make(data, box_size=10, border=4)
    stream = BytesIO()
    qr_image.save(stream, format='PNG')
    stream.seek(0)
    return HttpResponse(stream.getvalue(), content_type="image/png")