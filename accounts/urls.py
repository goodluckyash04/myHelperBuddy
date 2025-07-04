from django.urls import path

from .views.views import utilities,dashboard,index,about, profile, redirect_to_streamlit
from .views.view_auth import login,logout,forgotPassword,changePassword,signup, send_otp, generate_refresh_token, get_auth, authenticate_user
from .views.view_ledger_transaction import add_ledger_transaction, ledger_transaction_details, ledger_transaction, \
    update_ledger_transaction_status, delete_ledger_transaction, update_ledger_transaction, update_counterparty_name, \
    undo_ledger_transaction, fetch_deleted_ledger_transaction
from .views.view_transaction import create_transaction, transaction_detail, update_transaction, delete_transaction, \
    fetch_deleted_transaction, undo_transaction, update_transaction_status
from .views.view_financial_instrument import create_finance, finance_details, fetch_financial_transaction, \
    update_instrument_status, update_finance_detail, remove_instrument
from .views.view_task import addTask,currentMonthTaskReport,taskAction,editTask,taskReports
from .views.view_reminder import add_reminder,todays_reminder,reminder_list,cancel_reminder
from .views.view_music_downloader import music_download

    
urlpatterns = [

# ..........................................Home Page........................................................
    path("",index,name="index"),
    path("utilities/",utilities,name="utilities"),
    path("profile/",profile,name="profile"),
    path("dashboard/",dashboard,name="dashboard"),
    path("about/",about,name="about"),

# ..........................................User Management..................................................
    path("login",login,name="login"),
    path("signup/",signup,name="signup"),
    path("logout/",logout,name="logout"),
    path("send-otp/",send_otp,name="send_otp"),
    path("forgotPassword/",forgotPassword,name="forgotPassword"),
    path("changePassword/",changePassword,name="changePassword"),
    path("generate-refresh-token/",generate_refresh_token,name="generate-refresh-token"),
    path("get-auth/",get_auth,name="get-auth"),
    path("user-authentication/",authenticate_user,name="user-authentication"),

# ..........................................Transaction Management...........................................
    path("create-transaction/", create_transaction, name="create-transaction"),
    path("transaction-detail/", transaction_detail, name="transaction-detail"),
    path("deleted-transaction-detail/", fetch_deleted_transaction, name="deleted-transaction-detail"),
    path("update-transaction/<int:id>", update_transaction, name="update-transaction"),
    path("update-transaction-status/<int:id>", update_transaction_status, name="update-transaction-status"),
    path("delete-transaction/", delete_transaction,name="delete-transaction"),
    path("delete-transaction/<int:id>", delete_transaction ,name="delete-transaction"),
    path("undo-transaction/", undo_transaction, name="undo-transaction"),
    path("undo-transaction/<int:id>", undo_transaction, name="undo-transaction"),


# ..........................................Task Management..................................................
    path("addTask/",addTask,name="addTask"),
    path("currentMonthTaskReport/",currentMonthTaskReport,name="currentMonthTaskReport"),
    path("taskReports/",taskReports,name="taskReports"),
    path("editTask/<int:id>",editTask,name="editTask"),
    path("task/action/<int:id>/<str:action>/",taskAction,name="taskAction"),


# ..........................................Loan Management..................................................
    path("create-finance/",create_finance,name="create-finance"),
    path("finance-details/",finance_details,name="finance-details"),
    path("update-finance-detail/<int:id>",update_finance_detail,name="update-finance-detail"),
    path("fetch-financial-transaction/<int:id>",fetch_financial_transaction,name="fetch-financial-transaction"),
    path("update-instrument-status/<int:id>",update_instrument_status,name="update-instrument-status"),
    path("remove-instrument/<int:id>",remove_instrument,name="remove-instrument"),

# ..........................................Ledger Management..................................................
    path("create-ledger-transaction/", add_ledger_transaction, name="create-ledger-transaction"),
    path("ledger-transaction-details/", ledger_transaction_details, name="ledger-transaction-details"),
    path("ledger-transaction/<str:id>", ledger_transaction, name="ledger-transaction"),
    path("update-ledger-transaction-status/<int:id>", update_ledger_transaction_status, name="update-ledger-transaction-status"),
    path("update-ledger-transaction-status/", update_ledger_transaction_status, name="update-ledger-transaction-status"),
    path("delete-ledger-transaction/<int:id>", delete_ledger_transaction, name="delete-ledger-transaction"),
    path("update-ledger-transaction/<int:id>", update_ledger_transaction, name="update-ledger-transaction"),
    path("update-counterparty-name/<str:id>", update_counterparty_name, name="update-counterparty-name"),
    path("deleted-ledger-transaction/", fetch_deleted_ledger_transaction, name="deleted-ledger-transaction"),
    path("undo-ledger-transaction/", undo_ledger_transaction, name="undo-ledger-transaction"),
    path("undo-ledger-transaction/<int:id>", undo_ledger_transaction, name="undo-ledger-transaction"),

# ..........................................Reminder Management..................................................
    path('create-reminder/', add_reminder, name='add_reminder'),
    path('view-today-reminder/', todays_reminder, name='todays-reminder'),
    path('view-reminder/', reminder_list, name='view-reminders'),
    path('cancel-reminder/<int:id>', cancel_reminder, name='cancel-reminder'),


# ..........................................Music Management..................................................
    path('play-my-music/', music_download, name='music_download'),

# ..........................................Music Management..................................................
    path('advance-utils/', redirect_to_streamlit, name='advance-utils'),



]


