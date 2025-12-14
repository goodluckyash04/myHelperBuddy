# myHelperBuddy (MHB)

myHelperBuddy is a comprehensive, Django-based personal assistant web application designed to streamline and manage various aspects of your daily life. From tracking finances and tasks to managing documents and reminders, MHB serves as a central hub for personal productivity.

## 🚀 Key Features

### 1. 🔐 User Management
*   **Secure Authentication:** Robust login and signup system with OTP support.
*   **Profile Management:** Manage user profiles and settings.
*   **Security:** Password recovery and change password functionality.

### 2. 💰 Financial Management
*   **Expense Tracking:** Log and categorize transactions (Personal, Loan, Food, Shopping).
*   **Payment Modes:** Support for various payment methods like Credit Card, Online, and Cash.
*   **Financial Products:** Manage loans and other financial instruments with installment tracking.
*   **Ledger System:** Keep track of money lent to or borrowed from others (Counterparties).

### 3. ✅ Task Management
*   **Task Tracking:** Create, edit, and organize tasks with due dates.
*   **Prioritization:** Assign priority levels (Low, Medium, High) to tasks.
*   **Reports:** View monthly task performance and completion reports.

### 4. ⏰ Reminder System
*   **Flexible Scheduling:** Set Daily, Monthly, Yearly, or Custom recurring reminders.
*   **Dashboard:** Quickly view today's reminders to stay on top of your schedule.

### 5. 📂 Document Manager
*   **Secure Storage:** Upload and store important files.
*   **Protection:** Optional password protection for file downloads.
*   **Organization:** Tag files with keywords for easy retrieval.

### 6. 🛠️ Utilities & Extras
*   **Music Hub:** Integrated music downloader/player features.
*   **Advanced Tools:** Integration with Streamlit for advanced data utilities.
*   **Google Drive Integration:** Backup and storage capabilities using Google Drive API.

## 🛠️ Tech Stack

*   **Backend:** Python, Django
*   **Database:** SQLite (Default), JSON DB support
*   **Configuration:** python-decouple for environment management
*   **External APIs:** Google Drive API, Gmail SMTP

## ⚙️ Installation & Setup

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd myHelperBuddy
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    python -m venv venv
    # Windows
    venv\Scripts\activate
    # macOS/Linux
    source venv/bin/activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure Environment Variables:**
    Create a `.env` file in the project root (same level as `manage.py`) and add the following configurations (refer to `mysite/settings.py` for usage):

    ```env
    SECRET_KEY=your_secret_key
    DEBUG=True
    
    # Database
    DB_NAME=db.sqlite3
    JSON_DB=db.json
    
    # Email Settings
    EMAIL_HOST_USER=your_email@gmail.com
    EMAIL_HOST_PASSWORD=your_app_password
    
    # Security
    ENCRYPTION_KEY=your_encryption_key
    SALT=your_salt
    
    # Admin & Access Control
    ADMIN=admin_username
    ADMIN_EMAIL=admin_email
    ADMIN_ACCESS=True
    
    # Feature Flags (Set to True/False)
    REMINDER_USER_ACCESS=True
    FINANCE_USER_ACCESS=True
    TASK_USER_ACCESS=True
    TRANSACTION_USER_ACCESS=True
    LEDGER_USER_ACCESS=True
    OTHER_UTILITIES_USER_ACCESS=True
    MUSIC_USER_ACCESS=True
    DOCUMENT_MANAGER_USER_ACCESS=True
    
    # URLs
    SITE_URL=http://localhost:8000
    STREAMLIT_URL=http://localhost:8501
    
    # Google Drive API (If using backup features)
    CLIENT_ID=your_client_id
    CLIENT_SECRET=your_client_secret
    REDIRECT_URI=your_redirect_uri
    REFRESH_TOKEN=your_refresh_token
    TOKEN_URI=your_token_uri
    BACKUP_FOLDER_ID=your_folder_id
    
    # Document Manager Limits
    MAX_TOTAL_BYTES_PER_USER=104857600
    TOTAL_DB_FILE_SIZE=1073741824
    ```

5.  **Run Migrations:**
    ```bash
    python manage.py migrate
    ```

6.  **Create a Superuser:**
    ```bash
    python manage.py createsuperuser
    ```

7.  **Run the Server:**
    ```bash
    python manage.py runserver
    ```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

MyHelperBuddy – Proprietary License
Copyright (c) 2025, MyHelperBuddy. All rights reserved.

This software and associated documentation files (“Software”) are the exclusive
property of the copyright holder.

Unauthorized copying, reproduction, modification, distribution, transmission,
public display, or creating derivative works of the Software, in whole or in
part, by any means, is strictly prohibited without prior written permission
from the copyright owner.

You are granted a non-transferable, non-exclusive, revocable license to use
the Software solely for personal or authorized business purposes. You may not
sell, sublicense, rent, lease, or otherwise provide access to the Software to
any third party.

The Software is provided “AS IS” without warranty of any kind, express or
implied, including but not limited to warranties of merchantability, fitness
for a particular purpose, or non-infringement. In no event shall the copyright
holder be liable for any claim, damages, or other liability arising from the
use or inability to use the Software.

All rights not expressly granted are reserved by the copyright holder.