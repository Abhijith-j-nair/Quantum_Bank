from django.contrib import admin
from .models import CustomUser, Account, Transaction

# A class to improve the display of Accounts in the admin panel
class AccountAdmin(admin.ModelAdmin):
    list_display = ('user', 'account_number', 'account_type', 'balance')
    list_filter = ('account_type',)
    search_fields = ('user__username', 'account_number')

# A class to improve the display of Transactions in the admin panel
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'sender_account', 'receiver_account', 'amount', 'status')
    list_filter = ('status', 'transaction_type')
    search_fields = ('sender_account__account_number', 'receiver_account__account_number')

# Register your models with the admin site
admin.site.register(CustomUser)
admin.site.register(Account, AccountAdmin)
admin.site.register(Transaction, TransactionAdmin)