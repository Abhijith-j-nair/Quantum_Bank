from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from .models import Account, Transaction
import datetime

class ViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.client = Client()
        self.checking = Account.objects.create(
            user=self.user,
            account_type='Checking',
            balance=1000,
            account_number='CHK123'
        )
        self.savings = Account.objects.create(
            user=self.user,
            account_type='Savings',
            balance=5000,
            account_number='SAV456'
        )
        self.transaction = Transaction.objects.create(
            sender_account=self.checking,
            receiver_account=self.savings,
            amount=100,
            status='Completed'
        )

    def test_dashboard_view(self):
        self.client.login(username='testuser', password='12345')
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'CHK123')
        self.assertContains(response, '$1,000.00')

    def test_successful_transfer(self):
        self.client.login(username='testuser', password='12345')
        response = self.client.post(reverse('transfer'), {
            'from_account': self.checking.id,
            'recipient': 'SAV456',
            'amount': 100,
            'note': 'Test transfer'
        })
        self.assertEqual(response.status_code, 302)  # Redirect on success
        self.checking.refresh_from_db()
        self.assertEqual(self.checking.balance, 900)

    def test_transaction_list(self):
        self.client.login(username='testuser', password='12345')
        response = self.client.get(reverse('transactions') + '?start_date=2023-01-01')
        self.assertContains(response, self.transaction.transaction_id)

    def test_api_transaction_detail(self):
        self.client.login(username='testuser', password='12345')
        response = self.client.get(
            reverse('api_transaction_detail', args=[str(self.transaction.transaction_id)])
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('amount', response.json())