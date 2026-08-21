"""
Google Drive Service - OAuth authentication and Drive API operations.

This service handles:
- OAuth 2.0 authentication with refresh tokens
- Google Drive file operations (list, upload, download, delete)
- Service account authentication (alternative)
- Automatic token refresh and error notifications

Singleton pattern:
    Use `get_drive_service()` instead of `GoogleDriveService()` directly to
    reuse the already-initialized instance and avoid redundant token refreshes.
"""

import datetime
import io
import mimetypes
import os
import traceback
from typing import Dict, List, Optional, Tuple, Union
from urllib.parse import urlencode

import requests
from django.conf import settings
from google.auth import exceptions
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials as OAuthCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload, MediaIoBaseUpload

from accounts.models import RefreshToken
from .email_services import EmailService

# ---------------------------------------------------------------------------
# Module-level singleton — shared across the process lifetime.
# Use get_drive_service() to obtain the instance.
# ---------------------------------------------------------------------------
_drive_service_instance: "GoogleDriveService | None" = None


def get_drive_service() -> "GoogleDriveService":
    """
    Return the shared GoogleDriveService singleton, creating it on first call.

    The singleton is reused so that the cached access token is not thrown away
    and re-fetched on every request.  Call `instance.refresh_if_needed()` before
    any Drive API operation if you want to guarantee a live token without
    constructing a brand-new instance.

    Returns:
        GoogleDriveService: Shared, already-authenticated service instance.
    """
    global _drive_service_instance
    if _drive_service_instance is None or not _drive_service_instance.is_service_active:
        _drive_service_instance = GoogleDriveService()
    else:
        # Refresh the access token only when it is expired / about to expire.
        _drive_service_instance.refresh_if_needed()
    return _drive_service_instance


class GoogleDriveService:
    """
    Service for Google Drive API operations with OAuth 2.0 authentication.
    
    Features:
        - OAuth 2.0 authentication with automatic token refresh
        - File upload/download/list/delete operations
        - Service account authentication support
        - Error notification via email
        - Refresh token management
    """
    
    # OAuth endpoints
    AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    TOKEN_URL = "https://oauth2.googleapis.com/token"
    DRIVE_SCOPE = "https://www.googleapis.com/auth/drive"
    
    # Buffer (seconds) before actual expiry at which we proactively refresh.
    _EXPIRY_BUFFER_SECS = 300  # 5 minutes

    def __init__(self, use_oauth: bool = True):
        """
        Initialize Google Drive service.

        Prefer calling `get_drive_service()` over instantiating this class
        directly so that the cached access token is reused across requests.

        Args:
            use_oauth: If True, use OAuth 2.0; if False, use service account
        """
        self.email_service = EmailService()
        self.is_service_active = False
        # _token_expiry tracks when the cached access token expires so we can
        # avoid hitting Google's token endpoint on every single request.
        self._token_expiry: Optional[datetime.datetime] = None

        try:
            print("Initializing Google Drive Service...")

            # Get refresh token from database or settings
            token_obj = RefreshToken.objects.filter(
                is_active=True
            ).order_by('-created_at').first()

            self.refresh_token = (
                token_obj.refresh_token if token_obj
                else getattr(settings, 'REFRESH_TOKEN', None)
            )

            if use_oauth:
                self.creds = self.get_access_token()
                self.drive_service = build("drive", "v3", credentials=self.creds)
            else:
                self.drive_service = self.authenticate_with_service_account()

            self.is_service_active = True
            print("✅ Google Drive Service initialized successfully")

        except Exception as e:
            print(f"❌ Failed to initialize Google Drive Service: {e}")
            traceback.print_exc()
            self.is_service_active = False

    def _is_token_expired(self) -> bool:
        """Return True when the cached access token is absent or about to expire."""
        if self._token_expiry is None:
            return True
        buffer = datetime.timedelta(seconds=self._EXPIRY_BUFFER_SECS)
        return datetime.datetime.utcnow() >= (self._token_expiry - buffer)

    def refresh_if_needed(self) -> None:
        """
        Re-fetch the access token only when it is expired or about to expire.

        This is a no-op when the cached token still has more than
        `_EXPIRY_BUFFER_SECS` seconds of remaining lifetime, preventing
        unnecessary round-trips to Google's token endpoint.
        """
        if not self._is_token_expired():
            return
        print("🔄 Access token expired — refreshing...")
        self.creds = self.get_access_token()
        self.drive_service = build("drive", "v3", credentials=self.creds)
    
    def authenticate_with_service_account(self):
        """
        Authenticate using Google Service Account credentials.
        
        Returns:
            Google Drive service instance
            
        Raises:
            Exception: If authentication fails
        """
        try:
            credentials = service_account.Credentials.from_service_account_file(
                "cred.json",
                scopes=[self.DRIVE_SCOPE]
            )
            return build("drive", "v3", credentials=credentials)
        except exceptions.DefaultCredentialsError as e:
            raise Exception(f"Service Account Authentication failed: {str(e)}")
    
    @staticmethod
    def get_authentication_code_url() -> str:
        """
        Generate Google OAuth 2.0 authorization URL.

        This is a pure settings-read operation — it does NOT need an active
        Drive session or a valid access token.  Call it directly on the class::

            auth_url = GoogleDriveService.get_authentication_code_url()

        Returns:
            str: Authorization URL for the user to visit
        """
        params = {
            "client_id": settings.CLIENT_ID,
            "redirect_uri": settings.REDIRECT_URI,
            "response_type": "code",
            "scope": GoogleDriveService.DRIVE_SCOPE,
            "access_type": "offline",
            "prompt": "select_account consent",  # Force account picker and refresh token
        }
        return f"{GoogleDriveService.AUTH_URL}?{urlencode(params)}"

    # Backward-compat alias (instance calls still work)
    def get_authentication_code(self) -> str:
        """Backward-compatible alias — prefer `get_authentication_code_url()`."""
        return GoogleDriveService.get_authentication_code_url()

    @staticmethod
    def exchange_code_for_refresh_token(code: str, user) -> bool:
        """
        Exchange an OAuth authorization code for a long-lived refresh token.

        This is a pure HTTP operation — it does NOT need an active Drive session
        or a valid access token.  Call it directly on the class::

            success = GoogleDriveService.exchange_code_for_refresh_token(code, user)

        Args:
            code: Authorization code received from the OAuth callback
            user: Django User instance (token owner)

        Returns:
            bool: True if the refresh token was obtained and saved, False otherwise
        """
        data = {
            "code": code,
            "client_id": settings.CLIENT_ID,
            "client_secret": settings.CLIENT_SECRET,
            "redirect_uri": settings.REDIRECT_URI,
            "grant_type": "authorization_code",
        }
        try:
            response = requests.post(GoogleDriveService.TOKEN_URL, data=data, timeout=10)
            tokens = response.json()
            token = tokens.get("refresh_token")

            if token:
                RefreshToken.objects.create(refresh_token=token, created_by=user)
                print(f"✅ Refresh token created for user: {user.username}")
                return True

            print(f"❌ No refresh token in response: {tokens}")
            return False

        except Exception as e:
            print(f"❌ Error getting refresh token: {e}")
            traceback.print_exc()
            return False

    # Backward-compat alias (instance calls still work)
    def get_refresh_token(self, code: str, user) -> bool:
        """Backward-compatible alias — prefer `exchange_code_for_refresh_token()`."""
        return GoogleDriveService.exchange_code_for_refresh_token(code, user)

    def get_access_token(self) -> OAuthCredentials:
        """
        Fetch a fresh access token from Google using the stored refresh token.

        This method always performs a network round-trip to Google's token
        endpoint.  **Do not call it directly in hot paths** — use
        `refresh_if_needed()` or `get_drive_service()` instead so the token is
        only fetched when it has actually expired.

        The returned `OAuthCredentials` object has its `expiry` attribute set
        so that the google-auth library (and our own `_is_token_expired` check)
        can track lifetime correctly.

        Returns:
            OAuthCredentials: Google OAuth credentials with expiry set

        Raises:
            Exception: If token refresh fails
        """
        if not self.refresh_token:
            raise Exception("No refresh token available")

        data = {
            "client_id": settings.CLIENT_ID,
            "client_secret": settings.CLIENT_SECRET,
            "refresh_token": self.refresh_token,
            "grant_type": "refresh_token",
        }

        try:
            response = requests.post(settings.TOKEN_URI, data=data, timeout=10)
            response_data = response.json()

            if "access_token" in response_data:
                # Google returns expires_in (seconds); default to 3600 if missing.
                expires_in = int(response_data.get("expires_in", 3600))
                expiry = datetime.datetime.utcnow() + datetime.timedelta(seconds=expires_in)

                # Cache the expiry so refresh_if_needed() can skip future calls.
                self._token_expiry = expiry

                creds = OAuthCredentials(token=response_data["access_token"])
                # Set expiry on the credential object so google-auth can also
                # track it (e.g., if credentials.expired is checked elsewhere).
                creds.expiry = expiry
                print(f"✅ Access token fetched — expires at {expiry.strftime('%Y-%m-%d %H:%M:%S')} UTC")
                return creds

            # Handle errors
            if "error" in response_data:
                error_type = response_data.get('error')

                # Deactivate invalid refresh token
                if error_type == "invalid_grant":
                    token_obj = RefreshToken.objects.filter(
                        is_active=True
                    ).order_by('-created_at').first()

                    if token_obj:
                        token_obj.is_active = False
                        token_obj.deactivation_time = datetime.datetime.now()
                        token_obj.save()
                        print("❌ Refresh token deactivated due to invalid_grant")

                # Send error notification
                self.email_service.send_email(
                    subject="Google Drive Service Error",
                    recipient_list=[settings.ADMIN_EMAIL],
                    message=(
                        f"Google Drive Service Error\n\n"
                        f"Timestamp: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                        f"Error: {error_type}\n"
                        f"Description: {response_data.get('error_description', 'N/A')}\n\n"
                        f"Please refresh the access token in the admin panel."
                    )
                )

            raise Exception(f"Error getting access token: {response_data}")

        except requests.RequestException as e:
            raise Exception(f"Network error while refreshing token: {e}")
    
    # ========================================================================
    # File Operations
    # ========================================================================
    
    def list_files(
        self,
        folder_id: Optional[str] = None,
        mime_type: Optional[str] = None,
        page_size: int = 50,
        fields: str = "files(id, name, mimeType, size, modifiedTime, createdTime, parents)",
        order_by: Optional[str] = None
    ) -> List[Dict]:
        """
        List files from Google Drive with filtering and sorting.
        
        Args:
            folder_id: ID of folder to list from (None = all files)
            mime_type: Filter by MIME type (e.g., "application/pdf")
            page_size: Number of files to retrieve
            fields: Fields to include in response
            order_by: Sorting order (e.g., "name asc", "modifiedTime desc")
            
        Returns:
            List of file dictionaries with details
            
        Example:
            >>> service = GoogleDriveService()
            >>> files = service.list_files(mime_type="image/png", page_size=10)
        """
        query = ["trashed=false"]
        
        if folder_id:
            query.append(f"'{folder_id}' in parents")
        if mime_type:
            query.append(f"mimeType='{mime_type}'")
        
        request_params = {
            "q": " and ".join(query),
            "pageSize": page_size,
            "fields": fields,
        }
        
        if order_by:
            request_params["orderBy"] = order_by
        
        results = self.drive_service.files().list(**request_params).execute()
        files = results.get("files", [])
        
        # Add parent folder name to each file
        for file in files:
            parent_id = folder_id if folder_id else file.get("parents", [None])[0]
            folder_name = self.get_folder_name(parent_id) if parent_id else "Root"
            file["parentFolder"] = folder_name
        
        return files
    
    def get_folder_name(self, folder_id: str) -> str:
        """
        Get folder name by ID.
        
        Args:
            folder_id: Google Drive folder ID
            
        Returns:
            str: Folder name or "Unknown Folder"
        """
        try:
            folder = self.drive_service.files().get(
                fileId=folder_id,
                fields="name"
            ).execute()
            return folder.get("name", "Unknown Folder")
        except Exception:
            return "Unknown Folder"
    
    def upload_to_drive(
        self,
        file_source: Union[str, bytes],
        file_name: Optional[str] = None,
        folder_id: Optional[str] = None,
        mime_type: Optional[str] = None,
        is_memory_file: bool = True,
        resumable: bool = True
    ) -> Dict:
        """
        Upload a file to Google Drive.
        
        Args:
            file_source: File path (if is_memory_file=False) or bytes (if True)
            file_name: Name for the file (required if is_memory_file=True)
            folder_id: Destination folder ID (None = root)
            mime_type: MIME type (auto-detected if None)
            is_memory_file: Whether file_source is bytes or file path
            resumable: Use resumable upload (recommended for large files)
            
        Returns:
            dict: File details (id, name, mimeType, size)
            
        Example:
            >>> with open('document.pdf', 'rb') as f:
            ...     file_content = f.read()
            >>> result = service.upload_to_drive(
            ...     file_content,
            ...     file_name='document.pdf',
            ...     is_memory_file=True
            ... )
        """
        # Validate filename
        if file_name is None:
            if is_memory_file:
                raise ValueError("file_name must be provided when uploading from memory")
            file_name = os.path.basename(file_source)
        
        # Auto-detect MIME type
        if mime_type is None:
            mime_type = mimetypes.guess_type(file_name)[0] or "application/octet-stream"
        
        # Prepare file metadata
        file_metadata = {"name": file_name}
        if folder_id:
            file_metadata["parents"] = [folder_id]
        
        # Choose upload method
        if is_memory_file:
            media = MediaIoBaseUpload(
                io.BytesIO(file_source),
                mimetype=mime_type,
                resumable=resumable
            )
        else:
            media = MediaFileUpload(
                file_source,
                mimetype=mime_type,
                resumable=resumable
            )
        
        # Upload file
        file = self.drive_service.files().create(
            body=file_metadata,
            media_body=media,
            fields="id, name, mimeType, size"
        ).execute()
        
        print(f"✅ File uploaded: {file.get('name')} ({file.get('size')} bytes)")
        
        return file
    
    def download_file(self, file_id: str, save_path: str) -> None:
        """
        Download a file from Google Drive.
        
        Args:
            file_id: Google Drive file ID
            save_path: Local path to save file
            
        Example:
            >>> service.download_file('abc123', '/path/to/save/file.pdf')
        """
        request = self.drive_service.files().get_media(fileId=file_id)
        
        with open(save_path, "wb") as f:
            downloader = MediaIoBaseDownload(f, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()
                if status:
                    print(f"Download progress: {int(status.progress() * 100)}%")
        
        print(f"✅ File downloaded: {save_path}")
    
    def delete_file(self, file_id: str) -> None:
        """
        Delete a file from Google Drive.
        
        Args:
            file_id: Google Drive file ID
            
        Example:
            >>> service.delete_file('abc123')
        """
        self.drive_service.files().delete(fileId=file_id).execute()
        print(f"✅ File deleted: {file_id}")
