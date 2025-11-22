import os
import re

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from ..decorators import auth_user
from ..models import UploadedFile
from ..utilitie_functions import calculate_size, validate_uploaded_file


@auth_user
def upload_file(request, user):
    """Handles POST from the modern upload form (multipart)."""
    if request.method == "POST":
        uploaded = request.FILES.get("file")
        ok, err = validate_uploaded_file(uploaded)
        if not ok:
            messages.error(request, err)
            return HttpResponseRedirect(request.META.get("HTTP_REFERER"))

        if UploadedFile.objects.filter(
            owner=user, filename=uploaded.name, size=uploaded.size
        ).exists():
            messages.error(request, "File already exist.")
            return HttpResponseRedirect(request.META.get("HTTP_REFERER"))

        original_name = uploaded.name
        base, ext = os.path.splitext(original_name)
        pattern = rf"^{re.escape(base)} \(\d+\){re.escape(ext)}$"

        existing = UploadedFile.objects.filter(owner=user, filename__regex=pattern)
        count = existing.count()

        if existing:
            uploaded.name = f"{base} ({count + 1}){ext}"

        password = request.POST.get("download_password") or None

        keywords = request.POST.get("keywords", "").strip()
        uf = UploadedFile(
            owner=user,
            filename=uploaded.name,
            content_type=getattr(uploaded, "content_type", "")
            or "application/octet-stream",
            data=uploaded.read(),
            size=uploaded.size,
            keywords=keywords,
        )
        uf.set_download_password(password)
        uf.save()
        messages.success(request, "File uploaded successfully.")
        return HttpResponseRedirect(request.META.get("HTTP_REFERER"))


@auth_user
def list_files(request, user):
    """
    List files for current user with:
      - q (text) search across filename and keywords
      - tag (single tag) exact match against comma-separated keywords
    """
    qs = UploadedFile.objects.filter(owner=user).order_by("-uploaded_at")

    q = (request.GET.get("q") or "").strip()
    tag = (request.GET.get("tag") or "").strip().lower()  # normalize

    if q:
        # search filename OR keywords
        qs = qs.filter(Q(filename__icontains=q) | Q(keywords__icontains=q))

    if tag:
        # safer: find tag as a boundary in comma-separated keywords.
        # This regex looks for: ^tag, , tag, , tag$ or solitary tag
        # Use keywords__regex for a DB regex (Postgres, MySQL may differ on syntax)
        import re

        esc = re.escape(tag)
        # pattern matches:
        # - at start: 'tag' or 'tag,'
        # - in middle: ', tag' or ',tag'
        # - at end: ', tag' or ',tag' or entire value == tag
        # using word boundaries around commas/spaces
        regex = rf"(^|,\s*){esc}(\s*,|$)"
        qs = qs.filter(keywords__regex=regex)

    # Optional: paginate (recommended if many files)
    from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator

    page = request.GET.get("page", 1)
    paginator = Paginator(qs, 24)  # 24 cards per page
    try:
        files_page = paginator.page(page)
    except PageNotAnInteger:
        files_page = paginator.page(1)
    except EmptyPage:
        files_page = paginator.page(paginator.num_pages)

    for file in files_page:
        file.password_protected = file.download_password_hash is not None
        file.size = calculate_size(file.size)

    context = {
        "files": files_page,
        "q": q,
        "tag": tag,
        "paginator": paginator,
        "user": user,
    }
    return render(request, "document_manager/document_list.html", context)


@auth_user
def update_file_details(request, user, pk):
    """Update filename, keywords, and password with old-password verification."""
    uf = get_object_or_404(UploadedFile, pk=pk, owner=user)

    if request.method == "POST":
        # --------------------
        # FILENAME UPDATE
        # --------------------
        new_filename = request.POST.get("filename", "").strip()
        if not new_filename:
            messages.error(request, "Filename cannot be empty.")
            return HttpResponseRedirect(request.META.get("HTTP_REFERER"))

        # sanitize filename
        new_filename = re.sub(r"[\/\\]+", "_", new_filename)
        base, ext = os.path.splitext(new_filename)
        if not ext:
            _, orig_ext = os.path.splitext(uf.filename)
            ext = orig_ext
            new_filename = f"{base}{ext}"

        # uniqueness
        qs = UploadedFile.objects.filter(owner=user).exclude(pk=uf.pk)
        if qs.filter(filename=new_filename).exists():
            b, e = os.path.splitext(new_filename)
            count = qs.filter(filename__startswith=f"{b} (").count()
            new_filename = f"{b} ({count + 1}){e}"

        # --------------------
        # KEYWORDS
        # --------------------
        keywords = request.POST.get("keywords", "").strip()

        # --------------------
        # PASSWORD LOGIC
        # --------------------
        old_pwd_input = request.POST.get("old_password", "").strip()
        new_pwd_input = request.POST.get("password", "").strip()
        clear_pwd = request.POST.get("clear_password") == "1"

        # If file has existing password
        if uf.download_password_hash:
            # Verify old password
            if not old_pwd_input:
                messages.error(request, "Enter current password to update it.")
                return HttpResponseRedirect(request.META.get("HTTP_REFERER"))

            if not uf.check_download_password(old_pwd_input):
                messages.error(request, "Current password is incorrect.")
                return HttpResponseRedirect(request.META.get("HTTP_REFERER"))

            # If user wants to clear password
            if clear_pwd:
                uf.set_download_password(None)
            # If user sets new password
            elif new_pwd_input:
                uf.set_download_password(new_pwd_input)
            # else leave password unchanged

        else:
            # File has no existing password
            # Only set if provided
            if new_pwd_input:
                uf.set_download_password(new_pwd_input)
            # clear does nothing here

        # --------------------
        # SAVE ALL
        # --------------------
        uf.filename = new_filename
        uf.keywords = keywords
        uf.save()

        messages.success(request, "File updated successfully.")
        return HttpResponseRedirect(request.META.get("HTTP_REFERER"))

    messages.error(request, "Invalid request.")
    return HttpResponseRedirect(request.META.get("HTTP_REFERER"))


@auth_user
def download_file(request, user, pk):
    """Download handler. Owner can download w/o password. Others must POST password."""
    uf = get_object_or_404(UploadedFile, owner=user, pk=pk)

    pwd = request.POST.get("password") or ""

    if uf.download_password_hash and not pwd:
        messages.error(request, "Please provide a password to download this file.")
        return HttpResponseRedirect(request.META.get("HTTP_REFERER"))

    if uf.download_password_hash and not uf.check_download_password(pwd):
        messages.error(request, "Incorrect password.")
        return HttpResponseRedirect(request.META.get("HTTP_REFERER"))

    resp = HttpResponse(
        uf.data, content_type=uf.content_type or "application/octet-stream"
    )
    resp["Content-Disposition"] = f'attachment; filename="{uf.filename}"'
    return resp


@auth_user
def delete_file(request, user, pk):
    """Delete a file with optional password verification."""
    uf = get_object_or_404(UploadedFile, pk=pk, owner=user)

    if request.method == "POST":
        # If file is password protected
        if uf.download_password_hash:
            entered = request.POST.get("password", "").strip()

            if not entered:
                messages.error(request, "Enter password to delete this file.")
                return HttpResponseRedirect(request.META.get("HTTP_REFERER"))

            if not uf.check_download_password(entered):
                messages.error(request, "Incorrect password.")
                return HttpResponseRedirect(request.META.get("HTTP_REFERER"))

        # Delete file
        uf.delete()
        messages.success(request, "File deleted successfully.")
        return HttpResponseRedirect(request.META.get("HTTP_REFERER"))

    messages.error(request, "Invalid delete request.")
    return HttpResponseRedirect(request.META.get("HTTP_REFERER"))
