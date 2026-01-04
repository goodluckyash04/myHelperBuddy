"""
Document Manager Views

Handles file upload, listing, download, update, and deletion operations.

Features:
- File upload with size quota management
- Password-protected files
- Keyword tagging and search
- Pagination support
- Duplicate filename handling
- File type detection and icons
"""

import os
import re
from typing import Optional

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Q, Sum
from django.db.models.functions import Coalesce
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required

from accounts.models import UploadedFile
from accounts.utilitie_functions import (
    calculate_size,
    fetch_file_icon,
    validate_uploaded_file,
)


# ============================================================================
# File Upload
# ============================================================================

@login_required
def upload_file(request: HttpRequest) -> HttpResponse:
    """
    Handle file upload with validation and quota management.
    
    Features:
        - File validation (size, type, security)
        - Global storage limit check
        - Per-user quota enforcement
        - Duplicate detection
        - Automatic filename deduplication
        - Optional password protection
        - Keyword tagging
    
    Args:
        request: HTTP request with uploaded file
        
    Returns:
        HttpResponse: Redirect with success/error message
    """
    user = request.user
    if request.method != "POST":
        messages.error(request, "Invalid request method")
        return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))
    
    uploaded = request.FILES.get("file")
    if not uploaded:
        messages.error(request, "No file uploaded")
        return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))
    
    # Validate uploaded file
    ok, err = validate_uploaded_file(uploaded)
    if not ok:
        messages.error(request, err)
        return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))
    
    # Check for exact duplicate (same name and size)
    if UploadedFile.objects.filter(
        owner=user,
        filename=uploaded.name,
        size=uploaded.size
    ).exists():
        messages.error(request, "File already exists")
        return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))
    
    # Check global storage limit
    total_files_size = UploadedFile.objects.aggregate(
        total=Coalesce(Sum("size"), 0)
    )
    total_size_limit = int(settings.TOTAL_DB_FILE_SIZE) * 1024 * 1024  # MB to bytes
    
    if total_files_size.get("total", 0) > total_size_limit:
        if user.is_superuser:
            messages.error(
                request,
                f"Total file size has reached {settings.TOTAL_DB_FILE_SIZE} MB"
            )
        else:
            messages.error(
                request,
                "File upload service is currently unavailable. Please try again later."
            )
        return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))
    
    # Check per-user quota (non-superusers only)
    if not user.is_superuser:
        user_total = UploadedFile.objects.filter(owner=user).aggregate(
            total=Coalesce(Sum("size"), 0)
        )
        current_total = int(user_total.get("total", 0) or 0)
        new_total = current_total + (uploaded.size or 0)
        
        per_user_limit = int(settings.MAX_TOTAL_BYTES_PER_USER) * 1024 * 1024
        
        if new_total > per_user_limit:
            messages.error(
                request,
                f"File quota of {settings.MAX_TOTAL_BYTES_PER_USER} MB exceeded. "
                f"Currently using {calculate_size(current_total)}"
            )
            return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))
    
    # Handle duplicate filenames
    original_name = uploaded.name
    base, ext = os.path.splitext(original_name)
    
    # Check for existing files with pattern: "filename (n).ext"
    pattern = rf"^{re.escape(base)} \(\d+\){re.escape(ext)}$"
    existing_count = UploadedFile.objects.filter(
        owner=user,
        filename__regex=pattern
    ).count()
    
    if existing_count > 0:
        uploaded.name = f"{base} ({existing_count + 1}){ext}"
    
    # Get optional password and keywords
    password = request.POST.get("download_password") or None
    keywords = request.POST.get("keywords", "").strip()
    
    # Create file record
    uf = UploadedFile(
        owner=user,
        filename=uploaded.name,
        content_type=getattr(uploaded, "content_type", "") or "application/octet-stream",
        data=uploaded.read(),
        size=uploaded.size,
        keywords=keywords,
    )
    uf.set_download_password(password)
    uf.save()
    
    messages.success(request, f"File '{uploaded.name}' uploaded successfully")
    return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))


# ============================================================================
# File Listing
# ============================================================================

@login_required
def list_files(request: HttpRequest) -> HttpResponse:
    """
    List and search user's uploaded files with pagination.
    
    Features:
        - Search by filename or keywords
        - Filter by tag/keyword
        - Pagination (9 files per page)
        - File metadata (size, type, icon)
        - Password protection indicator
    
    Args:
        request: HTTP request with optional query params (q, tag, page)
    
    Returns:
        HttpResponse: Rendered document list template
    """
    user = request.user
    # Get all user files, ordered by upload date
    qs = UploadedFile.objects.filter(owner=user).order_by("-uploaded_at")
    
    # Add computed fields for display
    for file in qs:
        file.password_protected = file.download_password_hash is not None
        file.size = calculate_size(file.size)
        file.file_type, file.icon_class = fetch_file_icon(file.content_type)
    
    # Search query
    q = (request.GET.get("q") or "").strip()
    if q:
        qs = qs.filter(Q(filename__icontains=q) | Q(keywords__icontains=q))
    
    # Tag filter
    tag = (request.GET.get("tag") or "").strip().lower()
    if tag:
        # Match tag as whole word in comma-separated keywords
        esc = re.escape(tag)
        regex = rf"(^|,\s*){esc}(\s*,|$)"
        qs = qs.filter(keywords__regex=regex)
    
    # Pagination
    per_page = 9
    paginator = Paginator(qs, per_page)
    page_num = request.GET.get("page", 1)
    
    try:
        files_page = paginator.page(page_num)
    except PageNotAnInteger:
        files_page = paginator.page(1)
    except EmptyPage:
        files_page = paginator.page(paginator.num_pages)
    
    # Build base query string for pagination links
    base_qs = request.GET.copy()
    base_qs.pop("page", None)
    base_qs = base_qs.urlencode()
    
    # Get elided page range for compact pagination (Django ≥3.2)
    try:
        page_range = list(
            files_page.paginator.get_elided_page_range(
                files_page.number,
                on_each_side=1,
                on_ends=1
            )
        )
    except Exception:
        # Fallback to simple range for older Django versions
        page_range = list(files_page.paginator.page_range)
    
    context = {
        "files": files_page,
        "q": q,
        "tag": tag,
        "base_qs": base_qs,
        "page_range": page_range,
        "paginator": paginator,
        "user": user,
    }
    
    return render(request, "document_manager/document_list.html", context)


# ============================================================================
# File Update
# ============================================================================

@login_required
def update_file_details(request: HttpRequest, pk: int) -> HttpResponse:
    """
    Update file metadata (filename, keywords, password).
    
    Features:
        - Filename update with sanitization
        - Automatic duplicate filename handling
        - Keyword management
        - Password update/removal with verification
        - Old password verification for protected files
    
    Args:
        request: HTTP request with POST data
        pk: File primary key
        
    Returns:
        HttpResponse: Redirect with success/error message
    """
    user = request.user
    uf = get_object_or_404(UploadedFile, pk=pk, owner=user)
    
    if request.method != "POST":
        messages.error(request, "Invalid request method")
        return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))
    
    # ========================================================================
    # Filename Update
    # ========================================================================
    
    new_filename = request.POST.get("filename", "").strip()
    if not new_filename:
        messages.error(request, "Filename cannot be empty")
        return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))
    
    # Sanitize filename (remove path separators)
    new_filename = re.sub(r"[\/\\]+", "_", new_filename)
    
    # Preserve or add file extension
    base, ext = os.path.splitext(new_filename)
    if not ext:
        _, orig_ext = os.path.splitext(uf.filename)
        ext = orig_ext
        new_filename = f"{base}{ext}"
    
    # Check for duplicate filenames and auto-increment
    other_files = UploadedFile.objects.filter(owner=user).exclude(pk=uf.pk)
    if other_files.filter(filename=new_filename).exists():
        b, e = os.path.splitext(new_filename)
        count = other_files.filter(filename__startswith=f"{b} (").count()
        new_filename = f"{b} ({count + 1}){e}"
    
    # ========================================================================
    # Keywords Update
    # ========================================================================
    
    keywords = request.POST.get("keywords", "").strip()
    
    # ========================================================================
    # Password Update
    # ========================================================================
    
    old_pwd_input = request.POST.get("old_password", "").strip()
    new_pwd_input = request.POST.get("password", "").strip()
    clear_pwd = request.POST.get("clear_password") == "1"
    
    # If file has existing password
    if uf.download_password_hash:
        # Verify old password before making changes
        if not old_pwd_input:
            messages.error(request, "Enter current password to update file")
            return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))
        
        if not uf.check_download_password(old_pwd_input):
            messages.error(request, "Current password is incorrect")
            return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))
        
        # Clear password if requested
        if clear_pwd:
            uf.set_download_password(None)
        # Update to new password
        elif new_pwd_input:
            uf.set_download_password(new_pwd_input)
        # else: leave password unchanged
    
    else:
        # File has no password - set new one if provided
        if new_pwd_input:
            uf.set_download_password(new_pwd_input)
    
    # ========================================================================
    # Save All Changes
    # ========================================================================
    
    uf.filename = new_filename
    uf.keywords = keywords
    uf.save()
    
    messages.success(request, f"File '{new_filename}' updated successfully")
    return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))


# ============================================================================
# File Download
# ============================================================================

@login_required
def download_file(request: HttpRequest, pk: int) -> HttpResponse:
    """
    Download file with optional password protection.
    
    Owner can download without password. Password verification required
    if file is password-protected.
    
    Args:
        request: HTTP request with optional password in POST
        pk: File primary key
        
    Returns:
        HttpResponse: File download or redirect with error
    """
    user = request.user
    uf = get_object_or_404(UploadedFile, owner=user, pk=pk)
    
    # Check password if required
    pwd = request.POST.get("password", "")
    
    if uf.download_password_hash and not pwd:
        messages.error(request, "Password required to download this file")
        return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))
    
    if uf.download_password_hash and not uf.check_download_password(pwd):
        messages.error(request, "Incorrect password")
        return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))
    
    # Serve file download
    response = HttpResponse(
        uf.data,
        content_type=uf.content_type or "application/octet-stream"
    )
    response["Content-Disposition"] = f'attachment; filename="{uf.filename}"'
    
    return response


# ============================================================================
# File Deletion
# ============================================================================

@login_required
def delete_file(request: HttpRequest, pk: int) -> HttpResponse:
    """
    Delete file with optional password verification.
    
    Requires password verification if file is password-protected.
    
    Args:
        request: HTTP request with optional password in POST
        pk: File primary key
        
    Returns:
        HttpResponse: Redirect with success/error message
    """
    user = request.user
    uf = get_object_or_404(UploadedFile, pk=pk, owner=user)
    
    if request.method != "POST":
        messages.error(request, "Invalid delete request")
        return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))
    
    # Verify password if file is protected
    if uf.download_password_hash:
        entered = request.POST.get("password", "").strip()
        
        if not entered:
            messages.error(request, "Password required to delete this file")
            return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))
        
        if not uf.check_download_password(entered):
            messages.error(request, "Incorrect password")
            return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))
    
    # Delete file
    filename = uf.filename
    uf.delete()
    
    messages.success(request, f"File '{filename}' deleted successfully")
    return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))
