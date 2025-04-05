import datetime
import io
import os
import mimetypes
import requests
import webbrowser
from urllib.parse import urlencode

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials as OAuthCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseUpload, MediaIoBaseDownload

from .email_services import EmailService
from django.conf import settings

# pip install requests google-auth google-api-python-client
# pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client

    
class GoogleDriveService:
    def __init__(self):
        self.email_service = EmailService()
        try:
            self.creds = self.get_access_token()
            self.drive_service = build("drive", "v3", credentials=self.creds)
        except:
            pass

    def get_authentication_code(self):
        auth_url = "https://accounts.google.com/o/oauth2/v2/auth"
        params = {
            "client_id": settings.CLIENT_ID,
            "redirect_uri": settings.REDIRECT_URI,
            "response_type": "code",
            "scope": "https://www.googleapis.com/auth/drive",
            "access_type": "offline",
            "prompt": "select_account consent",  # 👈 Force account picker and refresh token
        }
        print(params)

        full_url = f"{auth_url}?{urlencode(params)}"
        webbrowser.open(full_url)

    def get_refresh_token(self, code):
        token_url = "https://oauth2.googleapis.com/token"
        data = {
            "code": code,
            "client_id": settings.CLIENT_ID,
            "client_secret": settings.CLIENT_SECRET,
            "redirect_uri": settings.REDIRECT_URI,
            "grant_type": "authorization_code"
        }
        response = requests.post(token_url, data=data)
        tokens = response.json()

        return tokens.get("refresh_token")  

    # generate access token
    def get_access_token(self):
        """Automatically refreshes OAuth access token."""
        response = requests.post(
            settings.TOKEN_URI,
            data={
                "client_id": settings.CLIENT_ID,
                "client_secret": settings.CLIENT_SECRET,
                "refresh_token": settings.REFRESH_TOKEN,
                "grant_type": "refresh_token",
            },
        )
        response_data = response.json()
        print(response_data)

        if "access_token" in response_data:
            return OAuthCredentials(token=response_data["access_token"])

        if "error" in response_data:
            self.email_service.send_email(
                subject="Error in Google services",
                recipient_list=[settings.ADMIN_EMAIL],
                message=(
                    f"Timestamp: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                    f"Error: {response_data.get('error')}\n"
                    f"Description: {response_data.get('error_description')}\n"
                )
            )
        
        raise Exception(f"Error getting access token: {response_data}")

     # Get files from Google Drive with filtering and sorting
    def list_files(self, folder_id=None, mime_type=None, page_size=50, fields="files(id, name, mimeType, size, modifiedTime, createdTime, parents)", order_by=None):
        """
        Lists files from Google Drive with filtering and sorting options.

        Args:
            folder_id (str, optional): ID of the folder to list files from. Defaults to None (lists all files).
            mime_type (str, optional): Filter by MIME type (e.g., "application/pdf"). Defaults to None.
            page_size (int, optional): Number of files to retrieve. Defaults to 50.
            fields (str, optional): Fields to retrieve. Defaults to "files(id, name, mimeType, size, modifiedTime, parents)".
            order_by (str, optional): Sorting order (e.g., "name asc", "modifiedTime desc"). Defaults to None.

        Returns:
            list: List of files with details.
        """
        query = ["trashed=false"]

        if folder_id:
            query.append(f"'{folder_id}' in parents")
        if mime_type:
            query.append(f"mimeType='{mime_type}'")

        query_string = " and ".join(query)

        request_params = {
            "q": query_string,
            "pageSize": page_size,
            "fields": fields,
        }
        if order_by:
            request_params["orderBy"] = order_by  # Apply ordering if provided

        results = self.drive_service.files().list(**request_params).execute()
        files = results.get("files", [])

        # Retrieve folder names dynamically
        for file in files:
            parent_id = folder_id if folder_id else file.get("parents", [None])[0]
            folder_name = self.get_folder_name(parent_id) if parent_id else "Root"
            file["parentFolder"] = folder_name

        return files
    
    # get_file_folder_name
    def get_folder_name(self, folder_id):
        folder = self.drive_service.files().get(fileId=folder_id, fields="name").execute()
        return folder.get("name", "Unknown Folder")

    # upload file to Google Drive
    def upload_to_drive(self, file_source, file_name=None, folder_id=None, mime_type=None, is_memory_file=True, resumable=True):
        """
        Uploads a file to Google Drive.

        Args:
            file_source (str | bytes): File path (if is_memory_file=False) or bytes content (if is_memory_file=True).
            file_name (str, optional): Name of the file. If None, extracts dynamically from file_source. Defaults to None.
            folder_id (str, optional): ID of the destination folder. Defaults to None (uploads to root).
            mime_type (str, optional): MIME type of the file. Defaults to auto-detection.
            is_memory_file (bool, optional): Whether the file is in-memory (True) or on disk (False). Defaults to True.
            resumable (bool, optional): Use resumable upload (recommended for large files). Defaults to True.

        Returns:
            dict: File details (ID, name, MIME type, size).
        """

        # Determine filename if not provided
        if file_name is None:
            if is_memory_file:
                raise ValueError("file_name must be provided when uploading from memory.")
            file_name = os.path.basename(file_source)

        # Auto-detect MIME type if not provided
        if mime_type is None:
            mime_type = mimetypes.guess_type(file_name)[0] or "application/octet-stream"

        file_metadata = {"name": file_name}
        if folder_id:
            file_metadata["parents"] = [folder_id]

        # Choose correct media upload method
        if is_memory_file:
            media = MediaIoBaseUpload(io.BytesIO(file_source), mimetype=mime_type, resumable=resumable)
        else:
            media = MediaFileUpload(file_source, mimetype=mime_type, resumable=resumable)

        # Upload file
        file = self.drive_service.files().create(body=file_metadata, media_body=media, fields="id, name, mimeType, size").execute()

        print(f"✅ File uploaded successfully: {file.get('name')}")

        return file

    def download_file(self, file_id, save_path):
        """Downloads a file from Google Drive."""
        request = self.drive_service.files().get_media(fileId=file_id)
        with open(save_path, "wb") as f:
            downloader = MediaIoBaseDownload(f, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()


    def delete_file(self, file_id):
        """Deletes a file from Google Drive."""
        self.drive_service.files().delete(fileId=file_id).execute()








