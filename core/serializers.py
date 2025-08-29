# core/serializers.py
from rest_framework import serializers
from .models import CustomUser, Account, Transaction

class CustomUserSerializer(serializers.ModelSerializer):
        class Meta:
            model = CustomUser
            fields = ['id', 'username', 'email', 'first_name', 'last_name', 'phone_number', 'address']
            read_only_fields = ['username', 'email'] # Prevent direct update of these via API if not desired

class AccountSerializer(serializers.ModelSerializer):
        user = CustomUserSerializer(read_only=True) # Nested serializer to show user details

        class Meta:
            model = Account
            fields = ['id', 'user', 'account_type', 'account_number', 'balance', 'created_at', 'updated_at']
            read_only_fields = ['account_number', 'balance', 'created_at', 'updated_at'] # Balance updated via transactions

class TransactionSerializer(serializers.ModelSerializer):
        sender_account = serializers.StringRelatedField() # Displays __str__ of Account
        receiver_account = serializers.StringRelatedField() # Displays __str__ of Account

        class Meta:
            model = Transaction
            fields = [
                'transaction_id', 'sender_account', 'receiver_account', 'amount',
                'transaction_type', 'description', 'timestamp', 'status',
                'hash', 'previous_block_hash', 'metadata'
            ]
            read_only_fields = [
                'transaction_id', 'timestamp', 'status', 'hash', 'previous_block_hash'
            ] # These are set by backend logic
    
from rest_framework import serializers
from .models import Transaction, Account

class AccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = ['account_number', 'account_type']

class TransactionSerializer(serializers.ModelSerializer):
    sender_account = AccountSerializer()
    receiver_account = AccountSerializer()
    
    class Meta:
        model = Transaction
        fields = '__all__'
