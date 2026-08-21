from accounts.views.views import get_counter_parties, get_counterparty_tabs_json

def ledger_modals_context(request):
    if request.user.is_authenticated:
        return {
            'counterparties': get_counter_parties(request.user),
            'counterparty_tabs_json': get_counterparty_tabs_json(request.user)
        }
    return {}
