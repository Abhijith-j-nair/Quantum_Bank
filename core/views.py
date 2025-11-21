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
import re 
from decimal import Decimal

from .models import Account, Transaction, CustomUser
from .forms import TransferForm, AccountCreationForm, UserProfileForm, SignUpForm
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

# --- UPDATED: SECURE VIEW TO EXECUTE TRANSFERS (SELF AND P2P) ---
@login_required
@transaction.atomic
def execute_chatbot_transfer(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=405)

    try:
        data = json.loads(request.body)
        amount_str = data.get('amount')
        from_acc_type = data.get('from_type')
        
        # Check if this is a P2P transfer (has a specific recipient account number)
        recipient_num = data.get('recipient_account_number')
        # Or a self-transfer (has a target account type)
        to_acc_type = data.get('to_type')

        if not amount_str or not from_acc_type:
            return JsonResponse({'status': 'error', 'message': 'Missing data.'}, status=400)

        # 1. Fetch Sender Account (Must belong to user)
        from_account = Account.objects.filter(user=request.user, account_type__iexact=from_acc_type).first()
        if not from_account:
            return JsonResponse({'status': 'error', 'message': f"You don't own a '{from_acc_type}' account."}, status=404)

        # 2. Fetch Receiver Account
        if recipient_num:
            # P2P Case: Find by account number
            to_account = Account.objects.filter(account_number=recipient_num).first()
        elif to_acc_type:
            # Self Case: Find by type belonging to user
            to_account = Account.objects.filter(user=request.user, account_type__iexact=to_acc_type).first()
        else:
             return JsonResponse({'status': 'error', 'message': "Target account not specified."}, status=400)

        if not to_account:
            return JsonResponse({'status': 'error', 'message': "Recipient account not found."}, status=404)

        # 3. Perform Balance Check
        amount = Decimal(amount_str)
        if from_account.balance < amount:
            return JsonResponse({'status': 'error', 'message': 'Insufficient funds.'}, status=400)

        # 4. Execute Transfer
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
        
        # Custom success message
        if recipient_num:
             msg = f"Successfully sent ₹{amount:,.2f} to {to_account.user.username}!"
        else:
             msg = f"Successfully transferred ₹{amount:,.2f} to your {to_account.account_type} account."

        return JsonResponse({'status': 'success', 'message': msg})

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


# --- UPDATED: CHATBOT API VIEW (PHASE 4) ---
@login_required
def chatbot_api_view(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        user_message = data.get('message', '').lower()
        bot_response = ""
        
        # --- Intent 1: Self Transfer ("transfer 100 from checking to savings") ---
        self_transfer_match = re.search(r'(transfer|move)\s+₹?(\d+(\.\d{1,2})?)\s+from\s+(checking|savings|investment)\s+to\s+(checking|savings|investment)', user_message)
        
        # --- Intent 2: Pay Another User ("pay 500 to jithu") ---
        # Default source is 'Checking'
        p2p_match = re.search(r'(pay|send)\s+₹?(\d+(\.\d{1,2})?)\s+to\s+([a-zA-Z0-9_@\.]+)', user_message)

        if self_transfer_match:
            amount = self_transfer_match.group(2)
            from_acc = self_transfer_match.group(4).capitalize()
            to_acc = self_transfer_match.group(5).capitalize()
            if from_acc == to_acc:
                return JsonResponse({'response': "You can't transfer money to the same account."})
            
            return JsonResponse({
                'type': 'confirmation',
                'message': f"I'm ready to transfer ₹{amount} from your {from_acc} to your {to_acc}. Please confirm.",
                'details': { 'amount': amount, 'from_type': from_acc, 'to_type': to_acc }
            })

        elif p2p_match:
            amount = p2p_match.group(2)
            recipient_name = p2p_match.group(4)
            
            # Logic to find the recipient (similar to transfer view)
            recipient_account = None
            
            # 1. Try Account Number
            recipient_account = Account.objects.filter(account_number=recipient_name).first()
            
            # 2. Try Username (if not found by number)
            if not recipient_account:
                try:
                    target_user = CustomUser.objects.get(username__iexact=recipient_name)
                    # Default to their Checking account
                    recipient_account = Account.objects.filter(user=target_user, account_type='Checking').first()
                    if not recipient_account:
                         # Fallback to any account
                         recipient_account = Account.objects.filter(user=target_user).first()
                except CustomUser.DoesNotExist:
                    pass

            if not recipient_account:
                return JsonResponse({'response': f"I couldn't find a user or account named '{recipient_name}'."})
            
            if recipient_account.user == request.user:
                return JsonResponse({'response': "You can't pay yourself using this command. Use 'transfer from checking to savings' instead."})

            return JsonResponse({
                'type': 'confirmation',
                'message': f"Found user {recipient_account.user.username} ({recipient_account.account_number}). Ready to send ₹{amount} from your Checking account. Confirm?",
                'details': { 
                    'amount': amount, 
                    'from_type': 'Checking', # Default source
                    'recipient_account_number': recipient_account.account_number 
                }
            })

        # --- Other Intents (Balance, History, FAQ) ---
        elif 'balance' in user_message:
            accounts = Account.objects.filter(user=request.user)
            if not accounts.exists():
                bot_response = "You don't have any accounts yet."
            else:
                bot_response = "Here are your account balances:\n"
                for acc in accounts:
                    bot_response += f"• {acc.account_type}: ₹{acc.balance:,.2f}\n"
            return JsonResponse({'response': bot_response})
        
        elif 'transaction' in user_message or 'history' in user_message:
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
            
        elif 'hello' in user_message or 'hi' in user_message:
            bot_response = f"Hello, {request.user.username}! You can say 'Pay 500 to Jithu' or 'Transfer 100 to savings'."
        else:
            bot_response = "I'm sorry, I don't understand. Try 'Pay 100 to [Username]' or ask for your balance."
        
        return JsonResponse({'response': bot_response})
    return JsonResponse({'error': 'Invalid request'}, status=400)