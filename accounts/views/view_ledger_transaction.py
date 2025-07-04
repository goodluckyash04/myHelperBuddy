import datetime
import decimal
import traceback
import json


from django.contrib import messages
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.db.models import Sum, Q, Value, DecimalField, ExpressionWrapper, F
from django.db.models.functions import Coalesce
from django.http import HttpResponseServerError, HttpResponseRedirect, JsonResponse
from django.shortcuts import redirect, render, get_object_or_404

from accounts.views.views import get_counter_parties

from ..decorators import auth_user
from ..models import LedgerTransaction
from .view_financial_instrument import desired_date




# ............................................Ledger Management...........................................

@auth_user
def add_ledger_transaction(request,user):
    try:
        transaction_type = request.POST.get('transaction_type','Receivable')
        transaction_date = request.POST.get('transaction_date')
        amount = decimal.Decimal(request.POST.get('amount',0.0))
        counterparty = request.POST.get('counterparty','').upper()
        description = request.POST.get('description','')
        no_of_installments = 1
        if request.POST.get('no_of_installments'):
            no_of_installments = int(request.POST.get('no_of_installments'))

        try:
            existing_transaction = LedgerTransaction.objects.get(
                transaction_type=transaction_type,
                transaction_date=transaction_date,
                amount=amount,
                counterparty=counterparty,
                description=description,
                created_by=user
            )
            if existing_transaction:
                raise ValueError(f"Same {transaction_type} Already Exist")

        except ObjectDoesNotExist:
            for index in range(0,no_of_installments):
                LedgerTransaction.objects.create(
                    transaction_type = transaction_type,
                    transaction_date = desired_date(transaction_date,index),
                    amount = amount,
                    status = 'Completed' if transaction_type in ('Received','Paid') else 'Pending',
                    completion_date = datetime.datetime.today() if transaction_type in ('Received','Paid') else None,
                    counterparty = counterparty,
                    description = description,
                    created_by = user
                )

            messages.success(request, f'{transaction_type}  Added')
            return HttpResponseRedirect(request.META.get('HTTP_REFERER'))    
    except ValidationError as e:
        messages.error(request, str(e))
        return HttpResponseRedirect(request.META.get('HTTP_REFERER'))    
    except ValueError as e:
        traceback.print_exc()
        messages.error(request, str(e))
        return HttpResponseRedirect(request.META.get('HTTP_REFERER'))    
    except Exception as e:
        messages.error(request, "An unexpected error occurred.")
        traceback.print_exc()
        return HttpResponseServerError()


@auth_user
def ledger_transaction_details(request,user):
    '''
    payable + completed = paid
    recivable + completed = recived
     '''
    try:
        def get_paid_and_received_sums(text):
            if text == "Paid":
                txn_types = ["Payable", "Paid"]
            else:
                txn_types = ["Receivable", "Received"]

            return Coalesce(
                Sum('amount', filter=Q(
                    (Q(transaction_type=txn_types[0], status='Completed') | Q(transaction_type=txn_types[1])) &
                    Q(created_by=user, is_deleted=False)
                )),
                Value(0, output_field=DecimalField())
            )

        def get_sum(text):
            return Coalesce(Sum('amount', filter=Q(transaction_type=text,created_by = user, is_deleted = False)),
                                      Value(0, output_field=DecimalField()))

        receivables_payables = LedgerTransaction.objects.filter(created_by=user).values('counterparty').annotate(
            total_receivable=get_sum("Receivable") - get_paid_and_received_sums("Received"),
            total_payable= get_sum("Payable") - get_paid_and_received_sums("Paid") 
        ).annotate(
    total=ExpressionWrapper(
        F('total_receivable') - F('total_payable') ,
        output_field=DecimalField()
    )
        )

        counterparties = get_counter_parties(user)
        return render(request, 'ledger_transaction/counterparty.html',{'user': user,'receivables_payables':receivables_payables,'counterparties':counterparties })
    except Exception as e:
        print(traceback.print_exc())
        messages.error(request, f"An error occurred: try again after some time")
        return render(request, "ledger_transaction/counterparty.html", {"user": user})


@auth_user
def ledger_transaction(request,id,user):
    try:
        search = request.GET.get('search', '')
        start = request.GET.get('start_d', '')
        end = request.GET.get('end_d', '')

        data_filter = Q(counterparty=id, is_deleted=False, created_by=user)
        if search:
            data_filter &= Q(description__icontains=search)
        if start and end:
            data_filter &= Q(transaction_date__gte=start, transaction_date__lte=end)
        ledger_trn = LedgerTransaction.objects.filter(data_filter).order_by('-transaction_date')
        query = {
            "search":search,
            "start":start,
            "end":end
        }
        return render(request, 'ledger_transaction/ledgerTransaction.html',{'user': user,'ledger_trn':ledger_trn,'counter_party':id,"query":query})
    except Exception as e:
        print(traceback.print_exc())
        messages.error(request, f"An error occurred: try again after some time")
        return render(request, "ledger_transaction/counterparty.html", {"user": user,'counter_party':id})


@auth_user
def update_ledger_transaction_status(request,user,id=None):
    try:
        if request.method == "GET":
            trasaction_list = [id]
        else:
            trasaction_list = request.POST.getlist('record_ids', '')

        for id in trasaction_list:
            entry = LedgerTransaction.objects.get(id=id,created_by = user)
            if entry.transaction_type in ("Receivable, Payable"):
                current_status = entry.status
                entry.status = "Completed" if current_status == "Pending" else "Pending"
                entry.completion_date = datetime.datetime.today() if current_status == "Pending" else None
                entry.save()
                if len(trasaction_list) == 1:
                    messages.success(request, f'Transaction Status Updated')
            else:
                if len(trasaction_list) == 1:
                    messages.info(request, f'Can not Update status of {entry.transaction_type} transaction')
                else:
                    pass
        return HttpResponseRedirect(request.META.get('HTTP_REFERER'))
    except Exception as e:
        print(traceback.print_exc())
        messages.error(request, f"An error occurred: will get back soon")
        return HttpResponseRedirect(request.META.get('HTTP_REFERER'))


@auth_user
def delete_ledger_transaction(request, id, user):
    try:
        current_product = LedgerTransaction.objects.get(created_by=user, id=id, is_deleted=False)
        current_product.is_deleted = True
        current_product.deleted_at = datetime.datetime.today()
        current_product.save()
        messages.success(request, f" Transaction deleted successfully.")
        return HttpResponseRedirect(request.META.get('HTTP_REFERER'))
    except Exception as e:
        messages.error(request, "An unexpected error occurred.")
        print(traceback.print_exc())
        return HttpResponseServerError()


# update-ledger-transaction
@auth_user
def update_ledger_transaction(request,id,user ):
    try:
        entry = get_object_or_404(LedgerTransaction, id=id, created_by=user)
        if request.method == "GET":
            task_dict = {
                'id': entry.id,
                'transaction_type': entry.transaction_type,
                'transaction_date': entry.transaction_date,
                'amount': entry.amount,
                'description': entry.description
            }
            return JsonResponse(task_dict)
        else:
            entry.transaction_type = request.POST['transaction_type']
            entry.transaction_date = request.POST['transaction_date']
            entry.amount = decimal.Decimal(request.POST['amount'])
            entry.description = request.POST['description']
            entry.save()
            messages.success(request, f'Updated Succesfully')
            return HttpResponseRedirect(request.META.get('HTTP_REFERER'))
    except Exception as e:
        messages.error(request, "An unexpected error occurred.")
        print(traceback.print_exc())
        return HttpResponseServerError()


@auth_user
def update_counterparty_name(request, id, user):
    if request.method == 'POST':
        try:
            # Parse JSON data from request body
            data = json.loads(request.body)
            new_counterparty = data.get('newCounterparty')

            if new_counterparty:
                transactions = LedgerTransaction.objects.filter(counterparty=id, created_by=user)
                for entry in transactions:
                    entry.counterparty = new_counterparty
                    entry.save()
                messages.success(request, 'Counterparty Updated Successfully')
            else:
                messages.error(request, 'Counterparty name is required.')

            return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

        except json.JSONDecodeError:
            messages.error(request, 'Invalid JSON data.')
            return HttpResponseServerError()

        except Exception as e:
            messages.error(request, 'An unexpected error occurred.')
            traceback.print_exc()
            return HttpResponseServerError()
    else:
        messages.error(request, 'Invalid request method.')
        return HttpResponseRedirect(request.META.get('HTTP_REFERER'))



@auth_user
def fetch_deleted_ledger_transaction(request, user):
    try:
        transaction_detail = LedgerTransaction.objects.filter(created_by=user,is_deleted =True).order_by('-deleted_at')
        return render(request, 'ledger_transaction/deletedLedgerEntries.html', {"data": transaction_detail, "user": user})
    except Exception as e:
        print(traceback.print_exc())
        messages.error(request, f"An error occurred: will get back soon")
        return redirect('utilities')



@auth_user
def undo_ledger_transaction(request, user,id=None):
    try:
        if request.method == "GET":
            undo_list = [id]
        else:
            undo_list = request.POST.getlist('record_ids', '')
        for id in undo_list:
            entry = LedgerTransaction.objects.get(id=id,created_by = user,is_deleted = True)
            if entry:
                entry.is_deleted = False
                entry.deleted_at = None
                entry.save()

        messages.success(request, f'Transaction Reversed')
        return HttpResponseRedirect(request.META.get('HTTP_REFERER'))
    except Exception as e:
        messages.error(request, f"An error occurred: will get back soon")
        return HttpResponseRedirect(request.META.get('HTTP_REFERER'))


