import hashlib
import json
from django.utils import timezone

def calculate_transaction_hash(transaction_instance):
    """
    Calculates the SHA-256 hash for a given Transaction instance.
    Ensure all relevant fields are included and ordered for consistent hashing.
    """
    data = {
        'transaction_id': str(transaction_instance.transaction_id),
        'sender_account_id': str(transaction_instance.sender_account.id),
        'receiver_account_id': str(transaction_instance.receiver_account.id) if transaction_instance.receiver_account else None,
        'amount': str(transaction_instance.amount), # Convert Decimal to string for consistent hashing
        'transaction_type': transaction_instance.transaction_type,
        'description': transaction_instance.description,
        'timestamp': transaction_instance.timestamp.isoformat(), # Use ISO format for consistent datetime string
        'previous_block_hash': transaction_instance.previous_block_hash,
    }
    # Sort keys to ensure consistent hash regardless of dictionary order
    encoded_data = json.dumps(data, sort_keys=True).encode('utf-8')
    return hashlib.sha256(encoded_data).hexdigest()

def verify_ledger_integrity():
    """
    Verifies the integrity of the entire transaction ledger.
    Returns (is_valid, total_blocks, last_block_hash, last_update_time).
    """
    from .models import Transaction # Import Transaction here to avoid circular import

    # Order by timestamp to ensure correct chain traversal
    transactions = Transaction.objects.filter(status='Completed').order_by('timestamp')
    is_valid = True
    current_hash_in_chain = '0' * 64 # Represents the hash of the "genesis block"

    for transaction in transactions:
        # 1. Verify previous_block_hash linkage
        if transaction.previous_block_hash != current_hash_in_chain:
            print(f"Chain integrity broken at transaction {transaction.transaction_id}: Expected previous hash {current_hash_in_chain}, got {transaction.previous_block_hash}")
            is_valid = False
            break

        # 2. Recalculate and verify current transaction's hash
        recalculated_hash = calculate_transaction_hash(transaction)
        if transaction.hash != recalculated_hash:
            print(f"Hash mismatch for transaction {transaction.transaction_id}: Stored {transaction.hash}, Recalculated {recalculated_hash}")
            is_valid = False
            break

        # Update current_hash_in_chain for the next iteration
        current_hash_in_chain = transaction.hash
    
    return is_valid, transactions.count(), current_hash_in_chain, timezone.now()
