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


class Task(models.Model):
    PRIORITY_CHOICES = [
        ("Low", _("Low")),
        ("Medium", _("Medium")),
        ("High", _("High")),
    ]
    STATUS_CHOICES = [
        ("Pending", _("Pending")),
        ("Completed", _("Completed")),
    ]

    priority = models.CharField(max_length=50, choices=PRIORITY_CHOICES, blank=True)
    name = models.CharField(max_length=100)
    complete_by_date = models.DateField()
    description = models.TextField(max_length=500, blank=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default="Pending")
    completed_on = models.DateField(blank=True, null=True)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateField(blank=True, null=True)
    created_by = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("Task")
        verbose_name_plural = _("Tasks")
        indexes = [
            models.Index(fields=['created_by']),
            models.Index(fields=['status']),
            models.Index(fields=['complete_by_date']),
            models.Index(fields=['is_deleted']),
            # Composite indexes
            models.Index(fields=['created_by', 'is_deleted']),
            models.Index(fields=['created_by', 'status']),
        ]


class LedgerTransaction(models.Model):
    STATUS_CHOICES = [
        ("Completed", _("Completed")),
        ("Pending", _("Pending")),
    ]
    transaction_type = models.CharField(max_length=50)
    transaction_date = models.DateField()
    amount = models.DecimalField(max_digits=15, decimal_places=2, default=0.0)
    counterparty = models.CharField(max_length=100)
    description = models.CharField(max_length=255)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="Pending")
    completion_date = models.DateField(blank=True, null=True)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateField(blank=True, null=True)
    created_by = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.counterparty

    class Meta:
        verbose_name = _("LedgerTransaction")
        verbose_name_plural = _("LedgerTransactions")
        indexes = [
            models.Index(fields=['created_by']),
            models.Index(fields=['status']),
            models.Index(fields=['transaction_date']),
            models.Index(fields=['is_deleted']),
            # Composite indexes
            models.Index(fields=['created_by', 'is_deleted']),
        ]


class Reminder(models.Model):
    DAILY = "daily"
    MONTHLY = "monthly"
    YEARLY = "yearly"
    CUSTOM = "custom"

    REMINDER_FREQUENCY_CHOICES = [
        (DAILY, "Daily"),
        (MONTHLY, "Monthly"),
        (YEARLY, "Yearly"),
        (CUSTOM, "Custom"),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField()
    reminder_date = models.DateField()
    frequency = models.CharField(
        max_length=10, choices=REMINDER_FREQUENCY_CHOICES, default=DAILY
    )
    custom_repeat_days = models.PositiveIntegerField(
        null=True, blank=True
    )  # Days for custom repetition
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateField(blank=True, null=True)
    created_by = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    class Meta:
        indexes = [
            models.Index(fields=['created_by']),
            models.Index(fields=['reminder_date']),
            models.Index(fields=['is_deleted']),
            models.Index(fields=['frequency']),
            # Composite indexes
            models.Index(fields=['created_by', 'is_deleted']),
            models.Index(fields=['created_by', 'reminder_date']),
        ]


class RefreshToken(models.Model):
    refresh_token = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    deactivation_at = models.DateField(blank=True, null=True)
    created_by = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.created_at


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
            from django.conf import settings
            return user.username == settings.ADMIN
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
