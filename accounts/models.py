
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class UserProfile(models.Model):
    user = models.OneToOneField(
        'auth.User', 
        on_delete=models.CASCADE, 
        related_name='profile'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s Profile"

    class Meta:
        verbose_name = _("User Profile")
        verbose_name_plural = _("User Profiles")







class FinancialProduct(models.Model):
    name = models.CharField(max_length=100)
    type = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=15, decimal_places=2, default=0.0)
    no_of_installments = models.IntegerField(default=0)
    started_on = models.DateField()
    status = models.CharField(
        max_length=20,
        choices=[("Open", _("Open")), ("Closed", _("Closed"))],
        default="Open",
    )
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateField(blank=True, null=True)
    created_by = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("Financial Product")
        verbose_name_plural = _("Financial Products")
        indexes = [
            models.Index(fields=['created_by']),
            models.Index(fields=['status']),
            models.Index(fields=['is_deleted']),
            # Composite indexes
            models.Index(fields=['created_by', 'is_deleted']),
            models.Index(fields=['created_by', 'status']),
        ]


class Transaction(models.Model):
    CATEGORY_CHOICES = [
        ("Personal", _("Personal")),
        ("Loan", _("Loan")),
        ("Food", _("Food")),
        ("Shopping", _("Shopping")),
    ]
    STATUS_CHOICES = [
        ("Completed", _("Completed")),
        ("Pending", _("Pending")),
    ]
    MODE_CHOICES = [
        ("CreditCard", _("CreditCard")),
        ("Online", _("Online")),
        ("Cash", _("Cash")),
    ]
    type = models.CharField(
        max_length=50
    )  # type is a reserved keyword, consider renaming this field
    category = models.CharField(
        max_length=50, choices=CATEGORY_CHOICES, default="Personal"
    )
    date = models.DateField()
    amount = models.DecimalField(max_digits=15, decimal_places=2, default=0.0)
    beneficiary = models.CharField(max_length=100)
    description = models.CharField(max_length=255)
    source = models.ForeignKey(
        FinancialProduct,
        on_delete=models.CASCADE,
        related_name="transactions",
        null=True,
        blank=True,
        default=None,
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="Pending")
    mode = models.CharField(max_length=10, choices=MODE_CHOICES, null=True)
    mode_detail = models.CharField(max_length=10, null=True)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateField(blank=True, null=True)
    created_by = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.description

    class Meta:
        verbose_name = _("Transaction")
        verbose_name_plural = _("Transactions")
        indexes = [
            models.Index(fields=['date']),
            models.Index(fields=['created_by']),
            models.Index(fields=['is_deleted']),
            models.Index(fields=['status']),
            models.Index(fields=['type']),
            models.Index(fields=['category']),
            # Composite indexes for common queries
            models.Index(fields=['created_by', 'is_deleted']),
            models.Index(fields=['created_by', 'is_deleted', 'date']),
            models.Index(fields=['created_by', 'is_deleted', 'status']),
        ]






class LedgerTransaction(models.Model):
    """
    Enhanced ledger transaction tracking with installment and partial payment support.
    
    Tracks financial transactions between user and entities (vendors, customers, partners).
    Supports installments, partial payments, and comprehensive audit trail.
    """
    
    # Transaction Type Choices
    TRANSACTION_TYPES = [
        ('RECEIVABLE', _('Money to Receive')),      # Pending incoming
        ('RECEIVED', _('Money Received')),          # Completed incoming
        ('PAYABLE', _('Money to Pay')),             # Pending outgoing
        ('PAID', _('Money Paid')),                  # Completed outgoing
    ]
    
    # Status Choices
    STATUS_CHOICES = [
        ('PENDING', _('Pending')),
        ('PARTIAL', _('Partially Paid')),
        ('COMPLETED', _('Completed')),
        ('CANCELLED', _('Cancelled')),
    ]
    
    # Payment Method Choices
    PAYMENT_METHODS = [
        ('CASH', _('Cash')),
        ('BANK_TRANSFER', _('Bank Transfer')),
        ('UPI', _('UPI')),
        ('CHEQUE', _('Cheque')),
        ('CARD', _('Card')),
        ('OTHER', _('Other')),
    ]
    
    # Core Fields
    transaction_type = models.CharField(
        max_length=20, 
        choices=TRANSACTION_TYPES,
        default='RECEIVABLE'
    )
    transaction_date = models.DateField()
    amount = models.DecimalField(max_digits=15, decimal_places=2, default=0.0)
    
    # Entity Information
    counterparty = models.CharField(max_length=100, db_index=True)
    # Sub-ledger tab — multiple parallel ledgers per counterparty
    tab_name = models.CharField(
        max_length=100,
        default='General',
        blank=True,
        db_index=True,
        help_text=_("Sub-ledger tab within this counterparty (e.g. 'Loan', 'Daily')")
    )

    # Transaction Details
    description = models.TextField()
    reference_number = models.CharField(
        max_length=50, 
        blank=True, 
        null=True,
        help_text=_("Transaction reference number")
    )
    # Status & Payment
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='PENDING'
    )
    payment_method = models.CharField(
        max_length=20, 
        choices=PAYMENT_METHODS, 
        blank=True, 
        null=True
    )
    
    # Payment Tracking
    paid_amount = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        default=0.0,
        help_text=_("Amount paid so far")
    )
    remaining_amount = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        default=0.0,
        help_text=_("Amount remaining to be paid")
    )
    
    # Due Date Management
    due_date = models.DateField(
        blank=True, 
        null=True,
        help_text=_("Due date for payment")
    )
    completion_date = models.DateField(
        blank=True, 
        null=True,
        help_text=_("Date when transaction was completed")
    )
    
    # Attachments & Notes
    notes = models.TextField(
        blank=True,
        help_text=_("Additional notes or comments")
    )
    
    # Tags for categorization
    tags = models.JSONField(
        default=list, 
        blank=True,
        help_text=_("Tags for categorization (e.g., ['supplies', 'materials'])")
    )
    
    # Audit Fields
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateField(blank=True, null=True)
    created_by = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("Ledger Transaction")
        verbose_name_plural = _("Ledger Transactions")
        ordering = ['-transaction_date', '-created_at']
        indexes = [
            models.Index(fields=['counterparty', 'is_deleted']),
            models.Index(fields=['created_by', 'transaction_date']),
            models.Index(fields=['status', 'due_date']),
            models.Index(fields=['created_by', 'is_deleted']),
            models.Index(fields=['transaction_type']),
        ]
    
    def __str__(self):
        return f"{self.counterparty} - {self.get_transaction_type_display()} - ₹{self.amount}"
    
    def save(self, *args, **kwargs):
        """Auto-calculate remaining amount and update status"""
        # Calculate remaining amount
        self.remaining_amount = self.amount - self.paid_amount
        
        # Auto-update status based on payment (only for RECEIVABLE/PAYABLE)
        if self.transaction_type in ['RECEIVABLE', 'PAYABLE']:
            if self.paid_amount == 0:
                if self.status != 'CANCELLED':
                    self.status = 'PENDING'
            elif self.paid_amount < self.amount:
                self.status = 'PARTIAL'
            elif self.paid_amount >= self.amount:
                self.status = 'COMPLETED'
                if not self.completion_date:
                    from django.utils import timezone
                    self.completion_date = timezone.now().date()
        
        super().save(*args, **kwargs)
    
    def get_payment_percentage(self):
        """Get payment completion percentage"""
        if self.amount == 0:
            return 0
        return int((self.paid_amount / self.amount) * 100)
    
    def is_overdue(self):
        """Check if transaction is overdue"""
        from django.utils import timezone
        if not self.due_date or self.status == 'COMPLETED':
            return False
        return timezone.now().date() > self.due_date
    
    def days_overdue(self):
        """Get number of days overdue"""
        from django.utils import timezone
        if not self.is_overdue():
            return 0
        return (timezone.now().date() - self.due_date).days


class PaymentRecord(models.Model):
    """
    Track individual payments against ledger transactions.
    
    Enables partial payment tracking with complete audit trail.
    Each payment records the amount, method, and optional receipt.
    """
    
    ledger_transaction = models.ForeignKey(
        LedgerTransaction,
        on_delete=models.CASCADE,
        related_name='payments',
        help_text=_("Ledger transaction this payment is for")
    )
    
    payment_date = models.DateField(help_text=_("Date payment was made/received"))
    amount_paid = models.DecimalField(
        max_digits=15, 
        decimal_places=2,
        help_text=_("Amount paid in this transaction")
    )
    payment_method = models.CharField(
        max_length=20, 
        choices=LedgerTransaction.PAYMENT_METHODS,
        help_text=_("Method of payment")
    )
    
    reference_number = models.CharField(
        max_length=50, 
        blank=True,
        help_text=_("Transaction reference number")
    )
    notes = models.TextField(
        blank=True,
        help_text=_("Additional notes about this payment")
    )
    
    created_by = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = _("Payment Record")
        verbose_name_plural = _("Payment Records")
        ordering = ['-payment_date', '-created_at']
        indexes = [
            models.Index(fields=['ledger_transaction', 'payment_date']),
            models.Index(fields=['created_by']),
        ]
    
    def __str__(self):
        return f"Payment ₹{self.amount_paid} on {self.payment_date}"
    
    def save(self, *args, **kwargs):
        """Update parent ledger transaction when payment is recorded"""
        super().save(*args, **kwargs)
        
        # Update parent transaction's paid amount
        transaction = self.ledger_transaction
        total_paid = sum(
            payment.amount_paid 
            for payment in transaction.payments.all()
        )
        transaction.paid_amount = total_paid
        transaction.save()  # This will trigger auto-status update





class RefreshToken(models.Model):
    refresh_token = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    deactivation_at = models.DateField(blank=True, null=True)
    created_by = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.created_at.strftime('%Y-%m-%d %H:%M:%S')


class UtilityModule(models.Model):
    """Registry for application utility modules with permission management"""
    
    ACCESS_TYPE_CHOICES = [
        ('PUBLIC', _('All Users')),
        ('CONFIG', _('Config-Based')),
        ('ADMIN', _('Admin Only')),
    ]
    
    # Module Identity
    key = models.CharField(
        max_length=50, 
        unique=True, 
        help_text=_("Unique module identifier (e.g., 'TRANSACTION', 'FINANCE')")
    )
    title = models.CharField(
        max_length=100, 
        help_text=_("Display title shown to users")
    )
    icon = models.CharField(
        max_length=50, 
        blank=True,
        help_text=_("Font Awesome icon class (e.g., 'fa-credit-card')")
    )
    
    # UI Configuration
    description = models.TextField(
        help_text=_("Module description displayed on utilities page")
    )
    url_pattern = models.CharField(
        max_length=200, 
        help_text=_("URL path for module (e.g., '/transaction-detail/')")
    )
    display_order = models.IntegerField(
        default=0, 
        help_text=_("Sort order in UI (lower numbers appear first)")
    )
    
    # Access Control
    access_type = models.CharField(
        max_length=20,
        choices=ACCESS_TYPE_CHOICES,
        default='CONFIG',
        help_text=_("Access control type: PUBLIC (all users), CONFIG (specific users), ADMIN (admin only)")
    )
    allowed_users_list = models.ManyToManyField(
        'auth.User',
        blank=True,
        related_name='accessible_modules',
        help_text=_("Select specific users who can access this module")
    )
    
    # State Management
    is_active = models.BooleanField(
        default=True, 
        help_text=_("Module enabled/disabled toggle")
    )
    show_on_landing = models.BooleanField(
        default=False,
        help_text=_("Display this module on the landing page (for non-logged-in users)")
    )
    landing_title = models.CharField(
        max_length=100,
        blank=True,
        help_text=_("Title to show on landing page (if different from main title)")
    )
    landing_description = models.TextField(
        blank=True,
        help_text=_("Description to show on landing page (if different from main description)")
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['display_order', 'title']
        verbose_name = _("Utility Module")
        verbose_name_plural = _("Utility Modules")
        indexes = [
            models.Index(fields=['key']),
            models.Index(fields=['is_active']),
            models.Index(fields=['display_order']),
            models.Index(fields=['is_active', 'display_order']),
        ]
    
    def __str__(self):
        return f"{self.title} ({self.key})"
    
    def save(self, *args, **kwargs):
        """Override save to clear cache when module is updated"""
        super().save(*args, **kwargs)
        # Clear the cache so changes take effect immediately
        from django.core.cache import cache
        cache.delete('utility_modules_registry')
    
    def has_access(self, user):
        """Check if a user has access to this module"""
        if not self.is_active:
            return False
        
        if self.access_type == 'PUBLIC':
            return True
        elif self.access_type == 'ADMIN':
            return user.is_superuser
        else:  # CONFIG
            # Check if user is in the selected users list
            # Updated to support both old and new user models during migration
            if hasattr(user, 'profile'): # New user
                return self.allowed_users_list.filter(id=user.id).exists()
            return self.allowed_users_list.filter(id=user.id).exists()





# ============================================================================
# Finance-First Core Models (Phase 2)
# ============================================================================

class Account(models.Model):
    """
    Represents a financial account (bank, cash, wallet).
    Used as the source/destination for all Entry transactions.
    """
    ACCOUNT_TYPE_CHOICES = [
        ('bank', _('Bank')),
        ('cash', _('Cash')),
        ('wallet', _('Wallet')),
    ]

    name = models.CharField(
        max_length=100,
        help_text=_("Account name, e.g. 'HDFC Bank', 'Cash', 'Paytm Wallet'")
    )
    account_type = models.CharField(
        max_length=20,
        choices=ACCOUNT_TYPE_CHOICES,
        default='bank',
    )
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        'auth.User',
        on_delete=models.CASCADE,
        related_name='finance_accounts',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.get_account_type_display()})"

    class Meta:
        verbose_name = _("Account")
        verbose_name_plural = _("Accounts")
        ordering = ['name']
        indexes = [
            models.Index(fields=['created_by', 'is_active']),
        ]


class Category(models.Model):
    """
    Expense or income category for Entry rows.
    Only used for expense/income entries.
    """
    CATEGORY_TYPE_CHOICES = [
        ('expense', _('Expense')),
        ('income', _('Income')),
    ]

    name = models.CharField(
        max_length=100,
        help_text=_("Category name, e.g. 'Food', 'Rent', 'Salary'")
    )
    category_type = models.CharField(
        max_length=20,
        choices=CATEGORY_TYPE_CHOICES,
        default='expense',
    )
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        'auth.User',
        on_delete=models.CASCADE,
        related_name='finance_categories',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.get_category_type_display()})"

    class Meta:
        verbose_name = _("Category")
        verbose_name_plural = _("Categories")
        ordering = ['name']
        indexes = [
            models.Index(fields=['created_by', 'is_active']),
            models.Index(fields=['created_by', 'category_type']),
        ]


class Loan(models.Model):
    """
    A loan with a fixed monthly EMI. Each month's payment is logged as
    Entry(entry_type='loan_emi') by the user. No auto-scheduling.
    """
    name = models.CharField(max_length=100, help_text=_("e.g. 'Bike Loan'"))
    principal = models.DecimalField(
        max_digits=15, decimal_places=2,
        help_text=_("Total principal - informational only"),
    )
    monthly_emi = models.DecimalField(
        max_digits=15, decimal_places=2,
        help_text=_("Fixed EMI amount per month, user-entered"),
    )
    account = models.ForeignKey(
        'Account', on_delete=models.PROTECT, related_name='loans',
    )
    start_date = models.DateField()
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='loans')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("Loan")
        verbose_name_plural = _("Loans")
        ordering = ['name']


class Investment(models.Model):
    """
    An investment (e.g. SIP) with a fixed monthly contribution.
    Each month's payment is logged as Entry(entry_type='investment_contribution').
    """
    name = models.CharField(max_length=100, help_text=_("e.g. 'SIP - Mutual Fund X'"))
    monthly_amount = models.DecimalField(
        max_digits=15, decimal_places=2,
        help_text=_("Fixed monthly contribution, user-entered"),
    )
    account = models.ForeignKey('Account', on_delete=models.PROTECT, related_name='investments')
    start_date = models.DateField()
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='investments')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("Investment")
        verbose_name_plural = _("Investments")
        ordering = ['name']


class SplitPlan(models.Model):
    """
    A lump-sum payment spread into N future monthly installments.
    When saved, auto-generates N Entry(entry_type='split_installment') rows (Phase 5).
    """
    title = models.CharField(max_length=100, help_text=_("e.g. 'New Phone - No Cost EMI'"))
    total_amount = models.DecimalField(max_digits=15, decimal_places=2)
    num_months = models.PositiveIntegerField(help_text=_("Number of installments"))
    start_month = models.DateField(
        help_text=_("First day of month when installments start")
    )
    account = models.ForeignKey('Account', on_delete=models.PROTECT, related_name='split_plans')
    created_by = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='split_plans')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = _("Split Plan")
        verbose_name_plural = _("Split Plans")
        ordering = ['-created_at']


class Entry(models.Model):
    """
    The single unified transaction ledger for all money movement.

    entry_type determines what kind of entry this is:
    - expense / income: regular transactions (category required)
    - loan_emi: monthly loan payment (linked_loan required)
    - investment_contribution: monthly SIP payment (linked_investment required)
    - split_installment: future installment from a SplitPlan (linked_split required)
    """
    ENTRY_TYPE_CHOICES = [
        ('expense', _('Expense')),
        ('income', _('Income')),
        ('loan_emi', _('Loan EMI')),
        ('investment_contribution', _('Investment Contribution')),
        ('split_installment', _('Split Installment')),
    ]

    account = models.ForeignKey(
        Account, on_delete=models.PROTECT, related_name='entries',
        help_text=_("Account this entry is charged to / credited from"),
    )
    entry_type = models.CharField(max_length=30, choices=ENTRY_TYPE_CHOICES, default='expense')
    amount = models.DecimalField(
        max_digits=15, decimal_places=2,
        help_text=_("Always positive; direction is determined by entry_type"),
    )
    date = models.DateField()
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='entries', help_text=_("Only for expense/income entries"),
    )
    note = models.CharField(max_length=255, blank=True)

    linked_loan = models.ForeignKey(
        Loan, on_delete=models.SET_NULL, null=True, blank=True, related_name='emi_entries',
    )
    linked_investment = models.ForeignKey(
        Investment, on_delete=models.SET_NULL, null=True, blank=True, related_name='contribution_entries',
    )
    linked_split = models.ForeignKey(
        SplitPlan, on_delete=models.SET_NULL, null=True, blank=True, related_name='installment_entries',
    )

    created_by = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='entries')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_entry_type_display()} Rs.{self.amount} on {self.date}"

    class Meta:
        verbose_name = _("Entry")
        verbose_name_plural = _("Entries")
        ordering = ['-date', '-created_at']
        indexes = [
            models.Index(fields=['created_by', 'date']),
            models.Index(fields=['created_by', 'entry_type']),
            models.Index(fields=['created_by', 'account']),
            models.Index(fields=['created_by', 'category']),
        ]


# ============================================================================
# Phase 6: Ledger Models
# ============================================================================

class LedgerContact(models.Model):
    """
    A person or entity with whom the user has financial transactions (given/taken).
    """
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20, blank=True)
    created_by = models.ForeignKey(
        'auth.User', on_delete=models.CASCADE, related_name='ledger_contacts'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("Ledger Contact")
        verbose_name_plural = _("Ledger Contacts")
        ordering = ['name']


class LedgerEntry(models.Model):
    """
    A specific ledger transaction (Given or Taken) with a contact.
    """
    TYPE_CHOICES = [
        ('given', _('Given (You lent money)')),
        ('taken', _('Taken (You borrowed money)')),
    ]
    STATUS_CHOICES = [
        ('open', _('Open')),
        ('settled', _('Settled')),
    ]

    contact = models.ForeignKey(
        LedgerContact, on_delete=models.CASCADE, related_name='ledger_entries'
    )
    entry_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    note = models.CharField(max_length=255, blank=True)
    
    # Track when the entry was marked as settled
    settled_at = models.DateTimeField(null=True, blank=True)

    created_by = models.ForeignKey(
        'auth.User', on_delete=models.CASCADE, related_name='ledger_entries'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.get_entry_type_display()} Rs.{self.amount} with {self.contact.name}"

    class Meta:
        verbose_name = _("Ledger Entry")
        verbose_name_plural = _("Ledger Entries")
        ordering = ['-date', '-created_at']
        indexes = [
            models.Index(fields=['created_by', 'contact']),
            models.Index(fields=['created_by', 'status']),
        ]


# ============================================================================
# Phase 8: CSV Import Staging
# ============================================================================

class StagingEntry(models.Model):
    """
    Temporary table to hold parsed CSV rows before user reviews and commits them.
    """
    SOURCE_CHOICES = [
        ('phonepe', _('PhonePe')),
        ('gpay', _('Google Pay')),
        ('other', _('Other')),
    ]
    STATUS_CHOICES = [
        ('pending', _('Pending Review')),
        ('committed', _('Committed')),
        ('duplicate', _('Duplicate (Skipped)')),
    ]

    source = models.CharField(max_length=20, choices=SOURCE_CHOICES)
    original_txn_id = models.CharField(
        max_length=100, 
        blank=True, 
        help_text=_("Transaction ID from CSV to prevent duplicates")
    )
    
    date = models.DateField()
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    entry_type = models.CharField(max_length=30, choices=Entry.ENTRY_TYPE_CHOICES)
    raw_description = models.CharField(max_length=500, blank=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    created_by = models.ForeignKey(
        'auth.User', on_delete=models.CASCADE, related_name='staging_entries'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.get_status_display()}] {self.date} - Rs.{self.amount}"

    class Meta:
        verbose_name = _("Staging Entry")
        verbose_name_plural = _("Staging Entries")
        ordering = ['date', 'created_at']
        indexes = [
            models.Index(fields=['created_by', 'status']),
            models.Index(fields=['original_txn_id']),
        ]
