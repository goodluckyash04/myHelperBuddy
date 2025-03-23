import traceback
import json

from datetime import datetime
from django.db.models import Q,Sum
from dateutil.relativedelta import relativedelta
from django.shortcuts import render,redirect
from django.conf import settings
from django.contrib import messages
from django.utils import timezone

from ..decorators import auth_user
from .view_reminder import calculate_reminder
from ..models import LedgerTransaction, Transaction
from ..utilitie_functions import format_amount,convert_decimal


USER_ACCESS = {
            "TRANSACTION_USER_ACCESS": settings.TRANSACTION_USER_ACCESS,
            "TASK_USER_ACCESS": settings.TASK_USER_ACCESS,
            "FINANCE_USER_ACCESS": settings.FINANCE_USER_ACCESS,
            "LEDGER_USER_ACCESS": settings.LEDGER_USER_ACCESS,
            "REMINDER_USER_ACCESS": settings.REMINDER_USER_ACCESS,
        }

def get_counter_parties(user):
    return LedgerTransaction.objects.filter(created_by=user).values_list('counterparty', flat=True).distinct()


def calculate_financial_overview(transactions):
    income = sum(entry.amount for entry in transactions if entry.type.lower() == 'income'and not entry.is_deleted)
    expense = sum(entry.amount for entry in transactions if entry.type.lower() == 'expense' and entry.date <= datetime.now().date())
    investment = sum(entry.amount for entry in transactions if entry.category.lower() == 'investment' and entry.date <= datetime.now().date())
    overdue = sum(entry.amount for entry in transactions if entry.category.lower() == 'emi'and entry.status.lower()=="pending")

    return {
        "Income": format_amount(income),
        "Expense": format_amount(expense - investment),
        "Saving": format_amount(income - expense),
        "Investment": format_amount(investment),
        "Due": format_amount(overdue),
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
    try:
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
    except:
        traceback.print_exc()
        # messages.error(request, "An unexpected error occurred.") 
        return redirect('error_500')

# ...........................................Home Page..................................................
@auth_user
def utilities(request,user):
    try:        
        utility_items = [
            {
                "key": "TRANSACTION_USER_ACCESS",
                "title": "TRANSACTION",
                "description": "Manage Your Money Moves, One Day at a Time!",
                "url": "/transaction-detail/",
            },
            {
                "key": "TASK_USER_ACCESS",
                "title": "TASK",
                "description": "Give Your Brain a Break, We've Got Your To-Dos Covered!",
                "url": "/currentMonthTaskReport/",
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
                "key": "REMINDER_USER_ACCESS",
                "title": "REMINDER",
                "description": "Never Miss a Moment, Let the Reminders Handle it All!",
                "url": "/view-today-reminder/",
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
    except:
        traceback.print_exc()
        # messages.error(request, "An unexpected error occurred.") 
        return redirect('error_500')


@auth_user
def profile(request, user):

    service_status = {key.replace("_USER_ACCESS", ""): user.username.lower() in value.split(",") or value=="*"  for key, value in USER_ACCESS.items()}
    
    return render(request, "profile.html", {"user":user, "service_status":service_status})

def error_500(request):  
    return render(request,"error_500.html",{'prev':request.META.get('HTTP_REFERER', '/')})


