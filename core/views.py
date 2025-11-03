# core/views.py
import uuid
from django.http import HttpResponse, JsonResponse
import qrcode
from io import BytesIO
from django.urls import reverse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.core.paginator import Paginator
from django.utils import timezone
from datetime import datetime
import json
import re # --- NEW: Import for regular expressions
from decimal import Decimal # --- NEW: Import for handling currency

from .models import Account, Transaction, CustomUser
from .forms import TransferForm, AccountCreationForm, UserProfileForm, SignUpForm
from .serializers import TransactionSerializer
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

# --- (All your existing views like generate_account_number, signup_view, etc. are here) ---
# ...
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
    if request.method == 'POST':
        form = TransferForm(request.POST, user=request.user)
        if form.is_valid():
            sender_account = form.cleaned_data['from_account']
            recipient_identifier = form.cleaned_data['recipient']
            amount = form.cleaned_data['amount']
            note = form.cleaned_data['note']

            try:
                receiver_account = Account.objects.filter(account_number=recipient_identifier).first()
                if not receiver_account:
                    recipient_user = CustomUser.objects.filter(
                        Q(email=recipient_identifier) | Q(username=recipient_identifier)
                    ).first()
                    if recipient_user:
                        receiver_account = Account.objects.filter(user=recipient_user).first()
                if not receiver_account:
                    messages.error(request, "Recipient account not found.")
                    return render(request, 'core/transfer.html', {'form': form})
                if sender_account.balance < amount:
                    messages.error(request, "Insufficient funds.")
                    return render(request, 'core/transfer.html', {'form': form})
                sender_account.balance -= amount
                receiver_account.balance += amount
                sender_account.save()
                receiver_account.save()
                Transaction.objects.create(
                    sender_account=sender_account,
                    receiver_account=receiver_account,
                    amount=amount,
                    transaction_type='Transfer',
                    description=note,
                    status='Completed'
                )
                messages.success(request, "Transfer completed successfully!")
                return redirect('dashboard')
            except Exception as e:
                messages.error(request, f"An error occurred: {e}")
                return render(request, 'core/transfer.html', {'form': form})
        else:
            return render(request, 'core/transfer.html', {'form': form})
    else:
        form = TransferForm(user=request.user)
    return render(request, 'core/transfer.html', {'form': form})

@login_required
def pay_me_view(request, account_number):
    recipient_account = get_object_or_404(Account, account_number=account_number)
    initial_data = {'recipient': recipient_account.account_number}
    form = TransferForm(user=request.user, initial=initial_data)
    return render(request, 'core/transfer.html', {'form': form, 'recipient_account': recipient_account})

@login_required
def transaction_list_view(request):
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    transactions_list = Transaction.objects.filter(
        Q(sender_account__user=request.user) | 
        Q(receiver_account__user=request.user)
    ).order_by('-timestamp')

    if start_date:
        start_date_obj = datetime.strptime(start_date, '%Y-%m-%d')
        transactions_list = transactions_list.filter(timestamp__gte=start_date_obj)
    if end_date:
        end_date_obj = datetime.strptime(end_date, '%Y-%m-%d')
        transactions_list = transactions_list.filter(timestamp__lte=end_date_obj)

    paginator = Paginator(transactions_list, 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    context = {
        'transactions': page_obj,
        'start_date': start_date,
        'end_date': end_date
    }
    return render(request, 'core/transactions.html', context)


@login_required
def account_detail_view(request, account_id):
    account = get_object_or_404(Account, id=account_id, user=request.user)
    transactions = Transaction.objects.filter(
        Q(sender_account=account) | Q(receiver_account=account)
    ).order_by('-timestamp')[:10]
    context = { 'account': account, 'recent_transactions': transactions }
    return render(request, 'core/account_detail.html', context)

@api_view(['GET'])
@login_required
def api_transaction_detail(request, transaction_id):
    try:
        transaction = Transaction.objects.get(
            Q(sender_account__user=request.user) | Q(receiver_account__user=request.user),
            transaction_id=transaction_id
        )
        serializer = TransactionSerializer(transaction)
        return Response(serializer.data)
    except Transaction.DoesNotExist:
        return Response({"error": "Transaction not found"}, status=404)

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

@login_required
def scan_and_pay_view(request):
    return render(request, 'core/scan.html')

# --- NEW: SECURE VIEW TO EXECUTE THE TRANSFER ---
@login_required
@transaction.atomic
def execute_chatbot_transfer(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=405)

    try:
        data = json.loads(request.body)
        amount_str = data.get('amount')
        from_acc_type = data.get('from_type')
        to_acc_type = data.get('to_type')

        if not all([amount_str, from_acc_type, to_acc_type]):
            return JsonResponse({'status': 'error', 'message': 'Missing data.'}, status=400)

        # Securely fetch accounts *owned by the logged-in user*
        from_account = Account.objects.filter(user=request.user, account_type__iexact=from_acc_type).first()
        to_account = Account.objects.filter(user=request.user, account_type__iexact=to_acc_type).first()

        if not from_account:
            return JsonResponse({'status': 'error', 'message': f"You don't own a '{from_acc_type}' account."}, status=404)
        if not to_account:
            return JsonResponse({'status': 'error', 'message': f"You don't own a '{to_acc_type}' account."}, status=404)

        amount = Decimal(amount_str)
        if from_account.balance < amount:
            return JsonResponse({'status': 'error', 'message': 'Insufficient funds.'}, status=400)

        # Perform the transfer
        from_account.balance -= amount
        to_account.balance += amount
        from_account.save()
        to_account.save()
        Transaction.objects.create(
            sender_account=from_account,
            receiver_account=to_account,
            amount=amount,
            transaction_type='Transfer',
            description='Transfer via AI Assistant',
            status='Completed'
        )
        return JsonResponse({'status': 'success', 'message': f'Transfer of ₹{amount:,.2f} to your {to_acc_type} account was successful!'})

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

# --- UPDATED: CHATBOT API VIEW (PHASE 3) ---
@login_required
def chatbot_api_view(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        user_message = data.get('message', '').lower()
        
        # --- Intent 1: Transaction ---
        # Try to parse a transfer request, e.g., "transfer 500 from checking to savings"
        transfer_match = re.search(r'(transfer|send) ₹?(\d+(\.\d{1,2})?) from (checking|savings|investment) to (checking|savings|investment)', user_message)
        if transfer_match:
            amount = transfer_match.group(2)
            from_acc_type = transfer_match.group(4).capitalize()
            to_acc_type = transfer_match.group(5).capitalize()

            if from_acc_type == to_acc_type:
                return JsonResponse({'response': "You can't transfer money to the same account."})

            # Propose the transaction
            return JsonResponse({
                'type': 'confirmation',
                'message': f"I'm ready to transfer ₹{amount} from your {from_acc_type} to your {to_acc_type} account. Please confirm.",
                'details': {
                    'amount': amount,
                    'from_type': from_acc_type,
                    'to_type': to_acc_type
                }
            })

        # --- Intent 2: Balance ---
        if 'balance' in user_message:
            accounts = Account.objects.filter(user=request.user)
            if not accounts.exists():
                bot_response = "You don't have any accounts yet."
            else:
                bot_response = "Here are your account balances:\n"
                for acc in accounts:
                    bot_response += f"• {acc.account_type}: ₹{acc.balance:,.2f}\n"
            return JsonResponse({'response': bot_response})
        
        # --- Intent 3: Transactions ---
        if 'transaction' in user_message or 'history' in user_message:
            txns = Transaction.objects.filter(
                Q(sender_account__user=request.user) | Q(receiver_account__user=request.user)
            ).order_by('-timestamp')[:3]
            if not txns.exists():
                bot_response = "You don't have any recent transactions."
            else:
                bot_response = "Here are your last 3 transactions:\n"
                for txn in txns:
                    bot_response += f"• ₹{txn.amount:,.2f} ({txn.transaction_type}) on {txn.timestamp.strftime('%d-%b-%Y')}\n"
            return JsonResponse({'response': bot_response})
            
        # --- Fallback (FAQ) Intents ---
        if 'password' in user_message or 'reset' in user_message:
            bot_response = "You can reset your password by logging out and using the 'Forgot Password?' link."
        elif 'qr code' in user_message or 'scan' in user_message:
            bot_response = "Your personal QR code is on the dashboard. To pay someone, use the 'Scan & Pay' link."
        elif 'hello' in user_message or 'hi' in user_message:
            bot_response = f"Hello, {request.user.username}! How can I help you today?"
        else:
            bot_response = "I'm sorry, I don't understand that. You can ask about your balance or recent transactions. You can also ask me to 'transfer 100 from checking to savings'."
        
        return JsonResponse({'response': bot_response})
    return JsonResponse({'error': 'Invalid request'}, status=400)