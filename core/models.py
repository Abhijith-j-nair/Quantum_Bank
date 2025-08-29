from django.db import models
from django.contrib.auth.models import AbstractUser  # For your custom user model
import uuid # For unique transaction IDs
from django.utils import timezone # For accurate timestamps
import hashlib # For hashing
import json    # For serializing data to hash

# core/models.py

class CustomUser (AbstractUser ):
    """
    Custom User model extending Django's AbstractUser .
    Add any additional user-specific fields here.
    """
    phone_number = models.CharField(max_length=15, blank=True, null=True, help_text="User 's phone number")
    address = models.TextField(blank=True, null=True, help_text="User 's residential address")
    # Example: Add a profile picture field
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)

    class Meta:
        verbose_name = "User "
        verbose_name_plural = "Users"

    def __str__(self):
        return self.username

class Account(models.Model):
    """
    Represents a bank account for a user.
    """
    user = models.ForeignKey(CustomUser , on_delete=models.CASCADE, related_name='accounts',
                             help_text="The user who owns this account.")
    
    account_number = models.CharField(max_length=20, unique=True,
                                      help_text="Unique identifier for the account.")
    
    ACCOUNT_TYPES = (
        ('Checking', 'Checking Account'),
        ('Savings', 'Savings Account'),
        ('Investment', 'Investment Account'),
    )
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPES,
                                    help_text="The type of this account (e.g., Checking, Savings).")
    
    balance = models.DecimalField(max_digits=15, decimal_places=2, default=0.00,
                                  help_text="Current balance of the account.")
    
    created_at = models.DateTimeField(auto_now_add=True,
                                      help_text="Timestamp when the account was created.")
    updated_at = models.DateTimeField(auto_now=True,
                                      help_text="Timestamp when the account was last updated.")

    class Meta:
        verbose_name = "Account"
        verbose_name_plural = "Accounts"
        unique_together = ('user', 'account_type')

    def __str__(self):
        return f"{self.user.username}'s {self.account_type} ({self.account_number})"

    def deposit(self, amount):
        if amount > 0:
            self.balance += amount
            self.save()
            return True
        return False

    def withdraw(self, amount):
        if amount > 0 and self.balance >= amount:
            self.balance -= amount
            self.save()
            return True
        return False

class Transaction(models.Model):
    """
    Represents a single transaction (ledger entry) in the banking system.
    Designed with blockchain-like integrity features.
    """
    transaction_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False,
                                      help_text="Unique identifier for this transaction.")
    
    sender_account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name='sent_transactions',
                                       help_text="The account from which funds were sent.")
    
    receiver_account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name='received_transactions',
                                         null=True, blank=True,
                                         help_text="The account to which funds were received (optional).")
    
    amount = models.DecimalField(max_digits=15, decimal_places=2,
                                 help_text="The amount of money involved in the transaction.")
    
    TRANSACTION_TYPES = (
        ('Transfer', 'Account Transfer'),
        ('Deposit', 'Deposit'),
        ('Withdrawal', 'Withdrawal'),
        ('Purchase', 'Purchase'),
        ('Bill Payment', 'Bill Payment'),
        ('Salary', 'Salary Deposit'),
    )
    transaction_type = models.CharField(max_length=50, choices=TRANSACTION_TYPES,
                                        help_text="The type of transaction.")
    
    description = models.CharField(max_length=255, blank=True, null=True,
                                   help_text="A brief description of the transaction.")
    
    timestamp = models.DateTimeField(default=timezone.now,
                                     help_text="The exact time and date of the transaction.")
    
    TRANSACTION_STATUSES = (
        ('Pending', 'Pending'),
        ('Completed', 'Completed'),
        ('Failed', 'Failed'),
        ('Reversed', 'Reversed'),
    )
    status = models.CharField(max_length=20, choices=TRANSACTION_STATUSES, default='Pending',
                              help_text="The current status of the transaction.")
    
    hash = models.CharField(max_length=64, unique=True, blank=True, null=True,
                            help_text="SHA-256 hash of this transaction's data for integrity.")
    
    previous_block_hash = models.CharField(max_length=64, blank=True, null=True,
                                           help_text="SHA-256 hash of the previous transaction in the ledger chain.")
    
    metadata = models.JSONField(blank=True, null=True,
                                help_text="Optional JSON field for additional transaction details.")

    class Meta:
        verbose_name = "Transaction"
        verbose_name_plural = "Transactions"
        ordering = ['timestamp']

    def __str__(self):
        return f"Txn {self.transaction_id} ({self.transaction_type}) - {self.amount} from {self.sender_account} to {self.receiver_account or 'N/A'}"

    def _calculate_hash(self):
        """
        Calculates the SHA-256 hash of the transaction's core data.
        The order of fields in the dictionary is important for consistent hashing.
        """
        data = {
            'transaction_id': str(self.transaction_id),
            'sender_account_id': str(self.sender_account.id),
            'receiver_account_id': str(self.receiver_account.id) if self.receiver_account else None,
            'amount': str(self.amount),
            'transaction_type': self.transaction_type,
            'description': self.description,
            'timestamp': self.timestamp.isoformat(),
            'previous_block_hash': self.previous_block_hash,
            'status': self.status,
        }
        encoded_data = json.dumps(data, sort_keys=True).encode('utf-8')
        return hashlib.sha256(encoded_data).hexdigest()

    def save(self, *args, **kwargs):
        if not self.pk: # Only on creation of a new transaction
            last_completed_transaction = Transaction.objects.filter(status='Completed').order_by('-timestamp').first()
            if last_completed_transaction:
                self.previous_block_hash = last_completed_transaction.hash
            else:
                self.previous_block_hash = '0' * 64 # Genesis block hash

            if not self.timestamp:
                self.timestamp = timezone.now()

            self.hash = self._calculate_hash()

        super().save(*args, **kwargs)
