from django.urls import path

from .views.view_auth import (
    authenticate_user,
    changePassword,
    check_email,
    check_username,
    forgotPassword,
    generate_refresh_token,
    get_auth,
    login,
    logout,
    send_otp,
    signup,
)
from .views.view_document_manager import (
    delete_file,
    download_file,
    list_files,
    update_file_details,
    upload_file,
)
from .views.view_financial_instrument import (
    create_finance,
    fetch_financial_transaction,
    finance_details,
    remove_instrument,
    update_finance_detail,
    update_instrument_status,
)
from .views.view_ledger_transaction import (
    add_ledger_transaction,
    delete_ledger_transaction,
    fetch_deleted_ledger_transaction,
    ledger_transaction,
    ledger_transaction_details,
    undo_ledger_transaction,
    update_counterparty_name,
    update_ledger_transaction,
    update_ledger_transaction_status,
)
from .views.view_music_downloader import music_download
from .views.view_reminder import (
    add_reminder,
    cancel_reminder,
    reminder_list,
    todays_reminder,
)
from .views.view_task import (
    addTask,
    currentMonthTaskReport,
    editTask,
    taskAction,
    taskReports,
)
from .views.view_transaction import (
    create_transaction,
    delete_transaction,
    fetch_deleted_transaction,
    transaction_detail,
    undo_transaction,
    update_transaction,
    update_transaction_status,
)
from .views.views import (
    about,
    dashboard,
    index,
    profile,
    redirect_to_streamlit,
    update_profile,
    utilities,
)

urlpatterns = [
    # ..........................................Home Page........................................................
    path("", index, name="index"),
    path("utilities/", utilities, name="utilities"),
    path("profile/", profile, name="profile"),
    path("update-profile/", update_profile, name="update-profile"),
    path("dashboard/", dashboard, name="dashboard"),
    path("about/", about, name="about"),
    # ..........................................User Management..................................................
    path("login", login, name="login"),
    path("signup/", signup, name="signup"),
    path("logout/", logout, name="logout"),
    path("send-otp/", send_otp, name="send_otp"),
    path("check-username/", check_username, name="check_username"),
    path("check-email/", check_email, name="check_email"),
    path("forgotPassword/", forgotPassword, name="forgotPassword"),
    path("changePassword/", changePassword, name="changePassword"),
    path(
        "generate-refresh-token/", generate_refresh_token, name="generate-refresh-token"
    ),
    path("get-auth/", get_auth, name="get-auth"),
    path("user-authentication/", authenticate_user, name="user-authentication"),
    # ..........................................Transaction Management...........................................
    path("create-transaction/", create_transaction, name="create-transaction"),
    path("transaction-detail/", transaction_detail, name="transaction-detail"),
    path(
        "deleted-transaction-detail/",
        fetch_deleted_transaction,
        name="deleted-transaction-detail",
    ),
    path("update-transaction/<int:id>", update_transaction, name="update-transaction"),
    path(
        "update-transaction-status/<int:id>",
        update_transaction_status,
        name="update-transaction-status",
    ),
    path("delete-transaction/", delete_transaction, name="delete-transaction"),
    path("delete-transaction/<int:id>", delete_transaction, name="delete-transaction"),
    path("undo-transaction/", undo_transaction, name="undo-transaction"),
    path("undo-transaction/<int:id>", undo_transaction, name="undo-transaction"),
    # ..........................................Task Management..................................................
    path("addTask/", addTask, name="addTask"),
    path(
        "currentMonthTaskReport/", currentMonthTaskReport, name="currentMonthTaskReport"
    ),
    path("taskReports/", taskReports, name="taskReports"),
    path("editTask/<int:id>", editTask, name="editTask"),
    path("task/action/<int:id>/<str:action>/", taskAction, name="taskAction"),
    # ..........................................Loan Management..................................................
    path("create-finance/", create_finance, name="create-finance"),
    path("finance-details/", finance_details, name="finance-details"),
    path(
        "update-finance-detail/<int:id>",
        update_finance_detail,
        name="update-finance-detail",
    ),
    path(
        "fetch-financial-transaction/<int:id>",
        fetch_financial_transaction,
        name="fetch-financial-transaction",
    ),
    path(
        "update-instrument-status/<int:id>",
        update_instrument_status,
        name="update-instrument-status",
    ),
    path("remove-instrument/<int:id>", remove_instrument, name="remove-instrument"),
    # ..........................................Ledger Management..................................................
    path(
        "create-ledger-transaction/",
        add_ledger_transaction,
        name="create-ledger-transaction",
    ),
    path(
        "ledger-transaction-details/",
        ledger_transaction_details,
        name="ledger-transaction-details",
    ),
    path("ledger-transaction/<str:id>", ledger_transaction, name="ledger-transaction"),
    path(
        "update-ledger-transaction-status/<int:id>",
        update_ledger_transaction_status,
        name="update-ledger-transaction-status",
    ),
    path(
        "update-ledger-transaction-status/",
        update_ledger_transaction_status,
        name="update-ledger-transaction-status",
    ),
    path(
        "delete-ledger-transaction/<int:id>",
        delete_ledger_transaction,
        name="delete-ledger-transaction",
    ),
    path(
        "update-ledger-transaction/<int:id>",
        update_ledger_transaction,
        name="update-ledger-transaction",
    ),
    path(
        "update-counterparty-name/<str:id>",
        update_counterparty_name,
        name="update-counterparty-name",
    ),
    path(
        "deleted-ledger-transaction/",
        fetch_deleted_ledger_transaction,
        name="deleted-ledger-transaction",
    ),
    path(
        "undo-ledger-transaction/",
        undo_ledger_transaction,
        name="undo-ledger-transaction",
    ),
    path(
        "undo-ledger-transaction/<int:id>",
        undo_ledger_transaction,
        name="undo-ledger-transaction",
    ),
    # ..........................................Reminder Management..................................................
    path("create-reminder/", add_reminder, name="add_reminder"),
    path("view-today-reminder/", todays_reminder, name="todays-reminder"),
    path("view-reminder/", reminder_list, name="view-reminders"),
    path("cancel-reminder/<int:id>", cancel_reminder, name="cancel-reminder"),
    # ..........................................Reminder Management..................................................
    path("upload-document/", upload_file, name="upload"),
    path("fetch-documents/", list_files, name="fetch_documents"),
    path("document/<int:pk>/update-details/", update_file_details, name="update_file_details"),
    path("document/<int:pk>/download/", download_file, name="download_file"),
    path("document/<int:pk>/delete/", delete_file, name="delete_file"),
    # ..........................................Music Management..................................................
    path("play-my-music/", music_download, name="music_download"),
    # ..........................................Music Management..................................................
    path("advance-utils/", redirect_to_streamlit, name="advance-utils"),
]
