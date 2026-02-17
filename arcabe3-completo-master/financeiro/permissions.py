from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect

from usuarios.models import get_or_create_user_organization

from .models import FinancialAccess


def get_financial_role(user):
    org = get_or_create_user_organization(user)
    access, _ = FinancialAccess.objects.get_or_create(organizacao=org, user=user, defaults={'role': FinancialAccess.ROLE_FULL})
    return access.role, org


def finance_view_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        role, _ = get_financial_role(request.user)
        if role == FinancialAccess.ROLE_NONE:
            messages.error(request, 'Sem acesso ao módulo financeiro.')
            return redirect('clientes')
        return view_func(request, *args, **kwargs)
    return wrapper


def finance_full_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        role, _ = get_financial_role(request.user)
        if role != FinancialAccess.ROLE_FULL:
            messages.error(request, 'Ação permitida apenas para perfil completo.')
            return redirect('financeiro_dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper
