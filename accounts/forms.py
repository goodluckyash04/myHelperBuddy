"""
Django forms for backend validation in myHelperBuddy application.
These forms provide server-side validation without affecting the existing UI/UX.
"""

from django import forms
from django.core.exceptions import ValidationError
from datetime import datetime
from .models import Transaction, LedgerTransaction, FinancialProduct


class TransactionForm(forms.ModelForm):
    """Form for validating transaction data."""
    
    class Meta:
        model = Transaction
        fields = ['type', 'category', 'date', 'amount', 'beneficiary', 
                  'description', 'source', 'status', 'mode', 'mode_detail']
    
    def clean_amount(self):
        """Validate that amount is positive."""
        amount = self.cleaned_data.get('amount')
        if amount is not None and amount <= 0:
            raise ValidationError("Amount must be greater than zero.")
        return amount
    
    def clean(self):
        """Additional validation logic."""
        cleaned_data = super().clean()
        transaction_type = cleaned_data.get('type')
        
        # If type is Income, set defaults
        if transaction_type == 'Income':
            cleaned_data['beneficiary'] = 'Self'
            cleaned_data['status'] = 'Completed'
            cleaned_data['mode'] = None
            cleaned_data['mode_detail'] = None
        
        return cleaned_data



class LedgerTransactionForm(forms.ModelForm):
    """Form for validating ledger transaction data."""
    
    class Meta:
        model = LedgerTransaction
        fields = ['transaction_type', 'transaction_date', 'amount', 
                  'counterparty', 'description', 'status', 'completion_date']
    
    def clean_amount(self):
        """Validate that amount is positive."""
        amount = self.cleaned_data.get('amount')
        if amount is not None and amount <= 0:
            raise ValidationError("Amount must be greater than zero.")
        return amount
    
    def clean_counterparty(self):
        """Validate and format counterparty name."""
        counterparty = self.cleaned_data.get('counterparty')
        if counterparty:
            return counterparty.strip().title()
        return counterparty
    
    def clean(self):
        """Validate completion_date based on status."""
        cleaned_data = super().clean()
        status = cleaned_data.get('status')
        completion_date = cleaned_data.get('completion_date')
        
        if status == 'Completed' and not completion_date:
            cleaned_data['completion_date'] = datetime.now().date()
        elif status == 'Pending':
            cleaned_data['completion_date'] = None
        
        return cleaned_data


class FinancialProductForm(forms.ModelForm):
    """Form for validating financial product data."""
    
    class Meta:
        model = FinancialProduct
        fields = ['name', 'type', 'amount', 'no_of_installments', 'started_on', 'status']
    
    def clean_amount(self):
        """Validate that amount is positive."""
        amount = self.cleaned_data.get('amount')
        if amount is not None and amount < 0:
            raise ValidationError("Amount cannot be negative.")
        return amount
    
    def clean_no_of_installments(self):
        """Validate number of installments."""
        no_of_installments = self.cleaned_data.get('no_of_installments')
        if no_of_installments is not None and no_of_installments < 0:
            raise ValidationError("Number of installments cannot be negative.")
        return no_of_installments
    
    def clean_name(self):
        """Validate and format product name."""
        name = self.cleaned_data.get('name')
        if name and len(name.strip()) < 2:
            raise ValidationError("Product name must be at least 2 characters long.")
        return name.strip()
