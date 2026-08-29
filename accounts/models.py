from django.contrib.auth.hashers import check_password, make_password
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class UserProfile(models.Model):
    user = models.OneToOneField(
        'auth.User', 
        on_delete=models.CASCADE, 
        related_name='profile'
    )
    profile_picture = models.ImageField(
        upload_to='profile_pictures/',
        null=True,
        blank=True,
        help_text="User profile picture"
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
        """Update parent ledger transaction when payment is recorded.

        Both writes (this payment record and the parent's paid_amount) are
        wrapped in a single atomic block so they always succeed or fail together.
        This prevents the balance from becoming inconsistent if an error occurs
        between the two saves.
        """
        from django.db import transaction as db_transaction

        with db_transaction.atomic():
            super().save(*args, **kwargs)

            # Recalculate total paid from all payment records for this ledger entry
            parent = self.ledger_transaction
            total_paid = sum(
                payment.amount_paid
                for payment in parent.payments.all()
            )
            parent.paid_amount = total_paid
            parent.save()  # triggers auto-status update in LedgerTransaction.save()


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


class UploadedFile(models.Model):
    owner = models.ForeignKey(
        'auth.User',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="uploaded_files",
    )
    filename = models.CharField(max_length=255)
    content_type = models.CharField(max_length=100, blank=True)
    data = models.BinaryField()
    keywords = models.CharField(max_length=500, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    download_password_hash = models.CharField(max_length=128, blank=True, null=True)

    # small metadata
    size = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return f"{self.filename} ({self.owner})"

    # helpers to set/check password
    def set_download_password(self, raw_password: str | None):
        if raw_password:
            self.download_password_hash = make_password(raw_password)
        else:
            self.download_password_hash = None

    def check_download_password(self, raw_password: str) -> bool:
        if not self.download_password_hash:
            return True  # no password required
        return check_password(raw_password or "", self.download_password_hash)

    def keyword_list(self):
        """Return normalized list of keywords (lowercase, stripped, unique keeping order)."""
        if not self.keywords:
            return []
        seen = set()
        out = []
        for k in (kw.strip() for kw in self.keywords.split(",") if kw.strip()):
            nk = k.lower()
            if nk in seen:
                continue
            seen.add(nk)
            out.append(nk)
        return out

    def set_keywords_from_list(self, kw_list):
        """Store keywords (list) back to comma-separated string with normalization."""
        cleaned = []
        seen = set()
        for k in kw_list:
            if not k:
                continue
            nk = k.strip().lower()
            if not nk or nk in seen:
                continue
            seen.add(nk)
            cleaned.append(nk)
        self.keywords = ", ".join(cleaned)



