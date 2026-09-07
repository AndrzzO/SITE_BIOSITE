"""Mecanismos centralizados de autorização e controle de acesso ao painel privado."""

from collections.abc import Callable
from functools import wraps
from typing import Any

from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse


def verificar_acesso_administrativo(user: Any) -> bool:
    """Verifica se o usuário possui todas as condições necessárias para acesso ao painel."""
    return bool(user and user.is_authenticated and user.is_active and user.is_staff)


class RequerAutenticacaoAdministrativaMixin:
    """
    Mixin para CBVs (Class-Based Views) que protege rotas da área administrativa.

    Regras:
    1. Usuários anônimos são redirecionados para a tela de login com parâmetro next.
    2. Usuários inativos ou sem flag is_staff recebem HTTP 403 Forbidden.
    """

    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        if not request.user.is_authenticated:
            return redirect_to_login(
                request.get_full_path(),
                login_url=settings.LOGIN_URL,
            )

        if not request.user.is_active:
            raise PermissionDenied("A conta informada está inativa.")

        if not request.user.is_staff:
            raise PermissionDenied("Acesso restrito a operadores administrativos da plataforma.")

        return super().dispatch(request, *args, **kwargs)  # type: ignore[misc]


def requer_autenticacao_administrativa(view_func: Callable) -> Callable:
    """Decorator para FBVs (Function-Based Views) protegendo endpoints administrativos."""

    @wraps(view_func)
    def _wrapped_view(request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        if not request.user.is_authenticated:
            return redirect_to_login(
                request.get_full_path(),
                login_url=settings.LOGIN_URL,
            )

        if not request.user.is_active:
            raise PermissionDenied("A conta informada está inativa.")

        if not request.user.is_staff:
            raise PermissionDenied("Acesso restrito a operadores administrativos da plataforma.")

        return view_func(request, *args, **kwargs)

    return _wrapped_view
