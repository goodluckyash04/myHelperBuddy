import re
import json

from datetime import datetime
from django.db.models import Q,Sum
from dateutil.relativedelta import relativedelta
from django.shortcuts import render,redirect
from django.conf import settings
from django.utils import timezone

from accounts.services.security_services import security_service

from ..decorators import auth_user
from .view_reminder import calculate_reminder
from ..models import LedgerTransaction, RefreshToken, Transaction
from ..utilitie_functions import format_amount,convert_decimal


USER_ACCESS = {
            "TRANSACTION_USER_ACCESS": settings.TRANSACTION_USER_ACCESS,
            "TASK_USER_ACCESS": settings.TASK_USER_ACCESS,
            "FINANCE_USER_ACCESS": settings.FINANCE_USER_ACCESS,
            "LEDGER_USER_ACCESS": settings.LEDGER_USER_ACCESS,
            "REMINDER_USER_ACCESS": settings.REMINDER_USER_ACCESS,
            "OTHER_UTILITIES_USER_ACCESS": settings.OTHER_UTILITIES_USER_ACCESS,
            "MUSIC_USER_ACCESS": settings.MUSIC_USER_ACCESS,
        }

def get_counter_parties(user):
    return LedgerTransaction.objects.filter(created_by=user).values_list('counterparty', flat=True).distinct()


def calculate_financial_overview(transactions):
    income = sum(entry.amount for entry in transactions if entry.type.lower() == 'income'and not entry.is_deleted)
    expense = sum(entry.amount for entry in transactions if entry.type.lower() == 'expense' and entry.category.lower() != 'investment' and entry.status.lower() == "completed")
    investment = sum(entry.amount for entry in transactions if entry.category.lower() == 'investment' and entry.status.lower() == "completed")
    
    overdue = sum(entry.amount for entry in transactions if entry.category.lower() == 'emi'and entry.status.lower()=="pending")
    split_due = sum(entry.amount for entry in transactions if re.search(r"Split\s\d{1,2}$", entry.description, re.IGNORECASE) and entry.status.lower()=="pending")
    
    return {
        "Income": format_amount(income),
        "Expense": format_amount(expense),
        "Saving": format_amount(income - expense - investment - split_due),
        "EMI Due":format_amount(overdue),
        "Investment": format_amount(investment),
        "Split Due": format_amount(split_due)
        # "Due (Split | EMI)": f"{format_amount(split_due)} |  {format_amount(overdue)}"
    }

def calculate_category_wise_expenses(transactions):
    category_wise_data = {}
    for txn in transactions.filter(type__iexact='Expense',date__lte = datetime.now().date()):
        category_wise_data[txn.category] = category_wise_data.get(txn.category, 0) + txn.amount
    return category_wise_data

def calculate_monthly_savings(transactions,user):
    current_date = timezone.now()

    last_12_months = [(current_date - relativedelta(months=i)).month for i in range(12)]
    last_12_months_years = [
        (current_date - relativedelta(months=i)).year for i in range(12)
    ]

    transactions = Transaction.objects.filter(
        created_by=user,
        is_deleted=False,
        date__year__in=last_12_months_years,
        date__month__in=last_12_months,
    ).values('date__year', 'date__month').annotate(
        total_expense=Sum('amount', filter=Q(type='Expense')),
        total_income=Sum('amount', filter=Q(type='Income'))
    )

    savings_data = {}
    for i in range(12):
        month = last_12_months[i]
        year = last_12_months_years[i]

        month_data = next(
            (transaction for transaction in transactions 
            if transaction['date__month'] == month and transaction['date__year'] == year), 
            {}
        )
        total_expense = month_data.get('total_expense') or 0
        total_income = month_data.get('total_income') or 0

        savings = total_income - total_expense
        label = datetime(year, month, 1).strftime("%b'%y")  # Format as Jan'24
        savings_data[label] = float(savings)

    return savings_data

def calculate_year_wise_data(transactions,user):
    current_date = timezone.now()

    first_day_of_next_month = datetime(current_date.year, current_date.month + 1, 1)
    if current_date.month == 12:
        first_day_of_next_month = datetime(current_date.year + 1, 1, 1)

    transactions = Transaction.objects.filter(
        created_by=user,
        is_deleted=False,
        date__lte=first_day_of_next_month,
    ).values('date__year').annotate(
        total_expense=Sum('amount', filter=Q(type='Expense')),
        total_income=Sum('amount', filter=Q(type='Income'))
    )
    year_wise_data = {} 
    year_wise_data['income'] = [i['total_income'] for i in transactions]
    year_wise_data['expense'] = [i['total_expense'] for i in transactions]
    year_wise_data['label'] = [i['date__year'] for i in transactions]
    return year_wise_data

def calculate_current_month_category_expenses(transactions, user):
    current_date = timezone.now()
    current_year = current_date.year
    current_month = current_date.month
    
    category_expenses = Transaction.objects.filter(
        created_by=user,
        is_deleted=False,
        date__month=current_month,
        date__year=current_year,
        type='Expense'
    ).values('category').annotate(
        amount=Sum('amount')
    )

    total = Transaction.objects.filter(
        created_by=user,
        is_deleted=False,
        date__month=current_month,
        date__year=current_year,
    ).values('type').annotate(
        amount=Sum('amount')
    )

    category_wise = {}

    category_wise['labels'] = [i['category'] for i in category_expenses]
    category_wise['amount'] = [i['amount'] for i in category_expenses]

    income_total = next((item['amount'] for item in total if item['type'] == 'Income'), 0)
    expense_total = next((item['amount'] for item in total if item['type'] == 'Expense'), 0)

    category_wise['labels'].append('Balance')
    category_wise['amount'].append(income_total - expense_total)
    return category_wise

   
# ...........................................Index..................................................
def index(request):
    if request.session.get('username'):
        return redirect('dashboard')
    data = [
        {
            "icon":"fa-credit-card",
            "title":"Smart Transaction Management",
            "description":"Track your daily expenses and income with a simple, intuitive system that automatically categorizes each transaction."
        },
        {
            "icon":"fa-wallet",
            "title":"Easy Finance Tracking",
            "description":"Stay on top of your loans and investments, with reminders for payment dates and detailed records."
        },
        {
            "icon":"fa-check-circle",
            "title":"Efficient Task Management",
            "description":"Organize your tasks, set reminders, and keep track of what matters most, all in one place."
        },
        {
            "icon":"fa-book",
            "title":"Comprehensive Ledger",
            "description":"Keep your financial records well-organized. Maintain accurate accounting with ease."
        },
        {
            "icon":"fa-tags",
            "title":"Price Tracker",
            "description":"Keep tabs on your favorite products and get the best deals with real-time price tracking."
        },
        {
            "icon":"fa-bell",
            "title":"Reminder Management",
            "description":"Never miss important dates with customizable reminders for bills, tasks, and events."
        }
    ]
    return render(request,"landing_page.html",{"data":data})

# ...........................................About..................................................
@auth_user
def about(request,user):
    return render(request,"about.html",{"user":user})

# ...........................................Dashboard..................................................
@auth_user
def dashboard(request,user):
    transactions = Transaction.objects.filter(created_by=user,is_deleted = False)        

    user_info = {}
    user_info['first_txn_date'] = min(entry.date for entry in transactions if entry.category.lower()) if transactions else "" 
    user_info['account_age'] = (timezone.now() - user.created_at).days

    # Financial Overview
    financial_data = calculate_financial_overview(transactions)
    
    context = {}
    # Category-wise expense calculations
    context['category_wise_data'] = calculate_category_wise_expenses(transactions)

    # Monthly savings of the last 12 months      
    context["savings"] = calculate_monthly_savings(transactions, user)

    # Year-wise income and expense
    context['year_wise_data'] = calculate_year_wise_data(transactions, user)

    # Current month's category-wise expense
    context["category_wise_month"] = calculate_current_month_category_expenses(transactions, user)

    context = {'data': json.dumps(context,default=convert_decimal),'financial_data':financial_data,'user_info':user_info,'user':user}

    return render(request,'dashboard.html',context=context)

# ...........................................Home Page..................................................
@auth_user
def utilities(request,user):
  
    utility_items = [
        {
            "key": "TRANSACTION_USER_ACCESS",
            "title": "TRANSACTION",
            "description": "Manage Your Money Moves, One Day at a Time!",
            "url": "/transaction-detail/",
        },
        {
            "key": "FINANCE_USER_ACCESS",
            "title": "FINANCE",
            "description": "Track Your Loans and Sips, No Slips!",
            "url": "/finance-details/",
        },
        {
            "key": "LEDGER_USER_ACCESS",
            "title": "LEDGER",
            "description": "Balance Your Payables and Receivables with Ease!",
            "url": "/ledger-transaction-details/",
        },
        {
            "key": "TASK_USER_ACCESS",
            "title": "TASK",
            "description": "Give Your Brain a Break, We've Got Your To-Dos Covered!",
            "url": "/currentMonthTaskReport/",
        },
        {
            "key": "REMINDER_USER_ACCESS",
            "title": "REMINDER",
            "description": "Never Miss a Moment, Let the Reminders Handle it All!",
            "url": "/view-today-reminder/",
        },
        # {
        #     "key": "MUSIC_USER_ACCESS",
        #     "title": "MUSIC",
        #     "description": "Easily listen music and stay updated in real-time.",
        #     "url": "/play-my-music/"
        # },
        {   
            "key": "OTHER_UTILITIES_USER_ACCESS",
            "title": "ADVANCE UTILITIES",
            "description": "Access and manage advanced utility tools integrated with your account.",
            "url": "/advance-utils/",
        },
    ]

    items = [
        {
            "title": item["title"],
            "description": item["description"],
            "url": item["url"],
        }
        for item in utility_items
        if user.username.lower() in USER_ACCESS[item["key"]].split(",") or USER_ACCESS[item["key"]] == "*"
    ]

    reminder_count = len(calculate_reminder(user))
    counterparties = get_counter_parties(user)
    return render(request,"utiltities.html",{"user":user,'items': items, "counterparties":counterparties,"badge":reminder_count})


@auth_user
def profile(request, user):    
    context={}
    context["user"] = user
    context["service_status"] = get_service_status(user)
    if user.username == settings.ADMIN:
        refresh_token_time = RefreshToken.objects.filter(is_active=True).order_by("-created_at").first()
        context["last_genration"] = refresh_token_time.created_at if refresh_token_time else "N/A"
    return render(request, "profile.html",context=context)

def get_service_status(user):
    return {key.replace("_USER_ACCESS", "").replace("_"," "): user.username.lower() in value.split(",") or value=="*"  for key, value in USER_ACCESS.items()}

@auth_user
def redirect_to_streamlit(request, user):
    token = security_service.encrypt_text({'user_id':user.id, 'username':user.username})
    return redirect(f"{settings.STREAMLIT_URL}?_id={token}")

