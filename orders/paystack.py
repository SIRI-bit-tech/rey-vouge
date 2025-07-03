import requests
from django.conf import settings
from decimal import Decimal

class PaystackAPI:
    BASE_URL = 'https://api.paystack.co'
    
    def __init__(self):
        self.secret_key = settings.PAYSTACK_SECRET_KEY
        self.headers = {
            'Authorization': f'Bearer {self.secret_key}',
            'Content-Type': 'application/json'
        }
    
    def initialize_payment(self, email, amount, reference, callback_url=None, metadata=None):
        """
        Initialize a payment transaction
        
        Args:
            email (str): Customer's email
            amount (Decimal): Amount in Naira
            reference (str): Unique transaction reference
            callback_url (str, optional): URL to redirect to after payment
            metadata (dict, optional): Additional data to store with transaction
            
        Returns:
            dict: Response from Paystack API
        """
        url = f"{self.BASE_URL}/transaction/initialize"
        
        # Convert amount to kobo (Paystack accepts amount in kobo)
        amount_in_kobo = int(amount * 100)
        
        payload = {
            "email": email,
            "amount": amount_in_kobo,
            "reference": reference,
            "callback_url": callback_url,
            "metadata": metadata or {}
        }
        
        response = requests.post(url, headers=self.headers, json=payload)
        return response.json()
    
    def verify_payment(self, reference):
        """
        Verify a payment transaction
        
        Args:
            reference (str): Transaction reference to verify
            
        Returns:
            dict: Payment verification details
        """
        url = f"{self.BASE_URL}/transaction/verify/{reference}"
        response = requests.get(url, headers=self.headers)
        return response.json()
    
    def get_transaction(self, transaction_id):
        """
        Get details of a transaction
        
        Args:
            transaction_id (int): Transaction ID
            
        Returns:
            dict: Transaction details
        """
        url = f"{self.BASE_URL}/transaction/{transaction_id}"
        response = requests.get(url, headers=self.headers)
        return response.json()
    
    def create_transfer_recipient(self, name, account_number, bank_code):
        """
        Create a transfer recipient for refunds
        
        Args:
            name (str): Account holder's name
            account_number (str): Bank account number
            bank_code (str): Bank code
            
        Returns:
            dict: Recipient creation response
        """
        url = f"{self.BASE_URL}/transferrecipient"
        payload = {
            "type": "nuban",
            "name": name,
            "account_number": account_number,
            "bank_code": bank_code,
            "currency": "NGN"
        }
        
        response = requests.post(url, headers=self.headers, json=payload)
        return response.json()
    
    def initiate_refund(self, transaction_id, amount=None):
        """
        Initiate a refund for a transaction
        
        Args:
            transaction_id (str): Transaction ID to refund
            amount (Decimal, optional): Amount to refund (if partial refund)
            
        Returns:
            dict: Refund response
        """
        url = f"{self.BASE_URL}/refund"
        payload = {
            "transaction": transaction_id
        }
        
        if amount:
            # Convert amount to kobo
            amount_in_kobo = int(amount * 100)
            payload["amount"] = amount_in_kobo
        
        response = requests.post(url, headers=self.headers, json=payload)
        return response.json() 