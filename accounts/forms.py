"""
Django forms for backend validation in myHelperBuddy application.
These forms provide server-side validation without affecting the existing UI/UX.
"""

from django import forms
from django.core.exceptions import ValidationError
from datetime import datetime
from .models import Transaction, Task, Reminder, LedgerTransaction, FinancialProduct


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


class TaskForm(forms.ModelForm):
    """Form for validating task data."""
    
    class Meta:
        model = Task
        fields = ['priority', 'name', 'complete_by_date', 'description', 'status']
    
    def clean_complete_by_date(self):
        """Validate that complete_by_date is not in the past for new tasks."""
        complete_by_date = self.cleaned_data.get('complete_by_date')
        if complete_by_date and not self.instance.pk:  # Only for new tasks
            if complete_by_date < datetime.now().date():
                raise ValidationError("Completion date cannot be in the past.")
        return complete_by_date
    
    def clean_name(self):
        """Validate task name."""
        name = self.cleaned_data.get('name')
        if name and len(name.strip()) < 3:
            raise ValidationError("Task name must be at least 3 characters long.")
        return name.strip()


class ReminderForm(forms.ModelForm):
    """Form for validating reminder data."""
    
    class Meta:
        model = Reminder
        fields = ['title', 'description', 'reminder_date', 'frequency', 'custom_repeat_days']
    
    def clean(self):
        """Validate frequency and custom_repeat_days."""
        cleaned_data = super().clean()
        frequency = cleaned_data.get('frequency')
        custom_repeat_days = cleaned_data.get('custom_repeat_days')
        
        if frequency == 'custom' and not custom_repeat_days:
            raise ValidationError("Custom repeat days is required for custom frequency.")
        
        if frequency != 'custom' and custom_repeat_days:
            cleaned_data['custom_repeat_days'] = None
        
        return cleaned_data
    
    def clean_title(self):
        """Validate title."""
        title = self.cleaned_data.get('title')
        if title and len(title.strip()) < 3:
            raise ValidationError("Title must be at least 3 characters long.")
        return title.strip()


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
