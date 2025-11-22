from django import forms

MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10 MB — adjust as needed
ALLOWED_CONTENT_TYPES = [
    "image/png",
    "image/jpeg",
    "application/pdf",
    "text/plain",
    "application/zip",
]  # adjust to your needs


class UploadForm(forms.Form):
    file = forms.FileField(label="Choose file")
    download_password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(render_value=False),
        help_text="Optional: set a password to protect downloads.",
    )

    def clean_file(self):
        f = self.cleaned_data["file"]
        if f.size > MAX_UPLOAD_SIZE:
            raise forms.ValidationError(
                f"File too large (max {MAX_UPLOAD_SIZE // (1024*1024)} MB)."
            )
        if (
            ALLOWED_CONTENT_TYPES
            and getattr(f, "content_type", None) not in ALLOWED_CONTENT_TYPES
        ):
            raise forms.ValidationError("This file type is not allowed.")
        return f


class UpdateFileForm(forms.Form):
    file = forms.FileField(required=True, label="Replace file")
    download_password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(render_value=False),
        help_text="Change or clear the download password. Leave blank to keep unchanged.",
    )

    def clean_file(self):
        f = self.cleaned_data["file"]
        if f.size > MAX_UPLOAD_SIZE:
            raise forms.ValidationError(
                f"File too large (max {MAX_UPLOAD_SIZE // (1024*1024)} MB)."
            )
        if (
            ALLOWED_CONTENT_TYPES
            and getattr(f, "content_type", None) not in ALLOWED_CONTENT_TYPES
        ):
            raise forms.ValidationError("This file type is not allowed.")
        return f


class DownloadPasswordForm(forms.Form):
    password = forms.CharField(
        required=False, widget=forms.PasswordInput, label="Download password"
    )
