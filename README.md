# myHelperBuddy

> Your intelligent companion for personal finance, productivity, and organization

![Django](https://img.shields.io/badge/Django-4.2.7-green)
![Python](https://img.shields.io/badge/Python-3.12+-blue)
![License](https://img.shields.io/badge/License-MIT-yellow)

**myHelperBuddy** is a comprehensive web application built with Django that helps you manage your finances, tasks, and documents all in one secure platform.

---

## ✨ Features

### 💰 Financial Management
- **Transaction Tracking**: Monitor income and expenses with advanced filtering and categorization
- **Loan & Investment Manager**: Track EMIs, SIPs, and split payments with automatic installment generation
- **Ledger System**: Manage receivables and payables with counterparty tracking
- **Financial Reports**: Get detailed analytics and summaries of your spending patterns

### ✅ Productivity Tools
- **Task Management**: Organize tasks with priorities, due dates, and status tracking
- **Smart Reminders**: Set flexible reminders (daily, monthly, yearly, custom intervals) with email notifications
- **Monthly Reports**: Track task completion and pending items

### 📁 Document Management
- **Secure Storage**: Upload and store documents with password protection
- **Smart Search**: Find files quickly with keyword and tag-based filtering
- **Quota Management**: Per-user storage limits with encryption
- **File Encryption**: All uploaded files are encrypted for maximum security

### 🔐 Security & Authentication
- **Google OAuth**: Sign in with your Google account
- **Email OTP**: Two-factor authentication for password recovery
- **Data Encryption**: Industry-standard encryption for sensitive data
- **Rate Limiting**: Protection against brute-force attacks

### 🔧 Admin Features
- **Automated Backups**: Daily database backups to Google Drive
- **Manual Backup**: Superusers can trigger backups from the profile page
- **Email Notifications**: Automated task reminder emails
- **Module Registry**: Dynamic feature management system

---

## 🚀 Quick Start

### Prerequisites
- Python 3.12 or higher
- pip (Python package manager)
- Virtual environment (recommended)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/goodluckyash04/myHelperBuddy.git
   cd myHelperBuddy/MHB_django/myHelperBuddy
   ```

2. **Create and activate virtual environment**
   ```bash
   # Windows
   python -m venv venv
   venv\Scripts\activate

   # Linux/Mac
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   
   Create a `.env` file in the project root:
   ```env
   SECRET_KEY=your-secret-key-here
   DEBUG=True
   ALLOWED_HOSTS=localhost,127.0.0.1
   
   # Database
   DB_NAME=db.sqlite3
   
   # Email Configuration
   EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
   EMAIL_HOST=smtp.gmail.com
   EMAIL_PORT=587
   EMAIL_USE_TLS=True
   EMAIL_HOST_USER=your-email@gmail.com
   EMAIL_HOST_PASSWORD=your-app-password
   
   # Admin Configuration
   ADMIN=admin_username
   ADMIN_EMAIL=admin@example.com
   ADMIN_ACCESS=True
   
   # Site Configuration
   SITE_URL=http://localhost:8000
   ENCRYPTION_KEY=your-encryption-key-here
   
   # Google OAuth (Optional)
   GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
   GOOGLE_CLIENT_SECRET=your-client-secret
   ```

5. **Run migrations**
   ```bash
   python manage.py migrate
   ```

6. **Create superuser**
   ```bash
   python manage.py createsuperuser
   ```

7. **Collect static files**
   ```bash
   python manage.py collectstatic
   ```

8. **Run the development server**
   ```bash
   python manage.py runserver
   ```

9. **Access the application**
   
   Open your browser and navigate to `http://localhost:8000`

---

## 📋 Configuration

### Google OAuth Setup

To enable Google Sign-In:

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable Google+ API
4. Create OAuth 2.0 credentials
5. Add authorized redirect URIs:
   ```
   http://localhost:8000/accounts/google/login/callback/
   ```
6. Copy the Client ID and Client Secret to your `.env` file

### Google Drive Backup Setup

For automated database backups to Google Drive:

1. Create a service account in Google Cloud Console
2. Download the JSON key file
3. Save it as `service_account.json` in the project root
4. Share your Google Drive folder with the service account email
5. Update your `.env` with the folder ID

### Email Configuration

For email notifications and OTP:

1. Use Gmail with App Password (recommended)
2. Go to Google Account Settings → Security → 2-Step Verification → App Passwords
3. Generate an app password
4. Add it to your `.env` file

---

## 🛠️ Technology Stack

### Backend
- **Django 4.2.7**: Web framework
- **Python 3.12**: Programming language
- **SQLite**: Database (can be switched to PostgreSQL)

### Frontend
- **Bootstrap 5.3**: UI framework
- **Font Awesome 6**: Icons
- **Custom CSS**: Theme styling
- **Vanilla JavaScript**: Interactivity

### Libraries & Services
- **django-allauth**: Authentication
- **Google APIs**: OAuth and Drive integration
- **Pillow**: Image processing
- **cryptography**: Data encryption
- **python-decouple**: Environment configuration

---

## 📚 Project Structure

```
myHelperBuddy/
├── accounts/                    # Main application
│   ├── management/
│   │   └── commands/
│   │       └── backup_db.py    # Database backup command
│   ├── middleware.py           # Custom middleware
│   ├── models.py               # Database models
│   ├── services/               # Business logic services
│   │   ├── email_services.py
│   │   ├── google_services.py
│   │   ├── module_registry.py
│   │   └── security_services.py
│   ├── static/                 # Static files
│   │   ├── css/
│   │   ├── js/
│   │   └── image/
│   ├── templates/              # HTML templates
│   ├── urls.py                 # URL routing
│   └── views/                  # View logic
│       ├── view_auth.py
│       ├── view_document_manager.py
│       ├── view_financial_instrument.py
│       ├── view_ledger_transaction.py
│       ├── view_reminder.py
│       ├── view_task.py
│       ├── view_transaction.py
│       └── views.py
├── mysite/                     # Project settings
│   ├── settings.py
│   └── urls.py
├── manage.py
├── requirements.txt
└── README.md
```

---

## 🔧 Management Commands

### Database Backup
```bash
# Backup with task reminders
python manage.py backup_db

# Backup without sending reminder emails
python manage.py backup_db --skip-reminders
```

### Other Commands
```bash
# Create database migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Collect static files
python manage.py collectstatic
```

---

## 🎨 Features Walkthrough

### Transaction Management
1. Navigate to Dashboard → Transactions
2. Click "Add Transaction" to create income/expense entries
3. Filter by date range, category, status, and payment mode
4. View financial summaries and analytics

### Financial Instruments
1. Go to Finance → Financial Instruments
2. Create loans or SIPs with automatic EMI generation
3. Track payment status and remaining balances
4. Manage split payments with automatic installments

### Task Management
1. Access Tasks → Add Task
2. Set priority, due date, and description
3. View monthly reports
4. Mark tasks as complete/incomplete

### Reminders
1. Navigate to Reminders → Add Reminder
2. Set frequency (daily, monthly, yearly, custom)
3. Receive daily email notifications
4. View today's reminders on dashboard

### Document Manager
1. Go to Documents → Upload
2. Add password protection (optional)
3. Tag and categorize files
4. Search and download securely

---

## 🔒 Security Features

- **CSRF Protection**: Built-in Django CSRF middleware
- **Password Hashing**: Secure password storage with Django's PBKDF2
- **Rate Limiting**: Custom middleware to prevent brute-force attacks
- **Data Encryption**: Sensitive data encrypted at rest
- **Secure Sessions**: HTTP-only cookies with secure flag in production
- **Input Validation**: Comprehensive form validation and sanitization

---

## 🚀 Deployment

### PythonAnywhere Deployment

1. Upload your code to PythonAnywhere
2. Create a virtual environment
3. Install requirements
4. Configure web app with WSGI file
5. Set environment variables in `/home/username/.env`
6. Reload web app

### Environment Variables for Production
```env
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
SECRET_KEY=your-production-secret-key
# ... other production settings
```

---

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

## 👤 Author

**Yash** - [goodluckyash04](https://github.com/goodluckyash04)

---

## 🤝 Contributing

Contributions, issues, and feature requests are welcome!

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📧 Support

For support, email your admin or open an issue in the repository.

---

## 🙏 Acknowledgments

- Django Documentation
- Bootstrap Team
- Font Awesome
- Google Cloud Platform

---

**Made with ❤️ and Django**