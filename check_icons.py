from accounts.models import UtilityModule

modules = UtilityModule.objects.all()[:5]
for m in modules:
    print(f"{m.key}: icon='{m.icon}'")
