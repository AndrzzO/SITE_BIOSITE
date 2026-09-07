"""Views para autenticação privada e workspace administrativo."""

import logging
from typing import Any

from django.conf import settings
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import resolve_url
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View
from django.views.generic import FormView, RedirectView, TemplateView

from .forms import AutenticacaoAdministrativaForm
from .permissoes import RequerAutenticacaoAdministrativaMixin, verificar_acesso_administrativo
from .servicos.rate_limit import ServicoRateLimitLogin

logger = logging.getLogger("aplicativos.administracao.seguranca")


class LoginAdministrativoView(FormView):
    """
    Controla o fluxo de autenticação da área privada da plataforma.

    Segurança:
    - Redireciona usuários já autenticados para o workspace.
    - Validação contra ataques de redirecionamento aberto (Open Redirect).
    - Registro de logs de auditoria para monitoramento de segurança.
    """

    form_class = AutenticacaoAdministrativaForm
    template_name = "painel/login.html"

    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        # Se o usuário já está autenticado como staff ativo, redireciona ao workspace
        if verificar_acesso_administrativo(request.user):
            redirect_to = self.get_success_url()
            return HttpResponseRedirect(redirect_to)
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self) -> dict[str, Any]:
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["next"] = self.request.GET.get("next", "")
        return context

    def form_valid(self, form: AutenticacaoAdministrativaForm) -> HttpResponse:
        user = form.get_user()
        auth_login(self.request, user)

        ip = ServicoRateLimitLogin.obter_ip_cliente(self.request)
        logger.info(
            "Login administrativo bem-sucedido para o operador '%s' a partir do IP %s",
            user.username,
            ip,
        )

        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self) -> str:
        """Determina a URL de destino pós-login com validação anti-open-redirect."""
        redirect_to = self.request.POST.get(
            "next",
            self.request.GET.get("next", ""),
        )

        url_is_safe = url_has_allowed_host_and_scheme(
            url=redirect_to,
            allowed_hosts={self.request.get_host()},
            require_https=self.request.is_secure(),
        )

        if not url_is_safe or not redirect_to:
            return resolve_url(settings.LOGIN_REDIRECT_URL)

        return redirect_to


class LogoutAdministrativoView(View):
    """
    Encerra a sessão administrativa de forma segura.

    Prioriza requisições POST para evitar operações sensíveis disparadas por GET ou links externos.
    """

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        if request.user.is_authenticated:
            ip = ServicoRateLimitLogin.obter_ip_cliente(request)
            logger.info(
                "Logout administrativo efetuado pelo operador '%s' a partir do IP %s",
                request.user.username,
                ip,
            )
            auth_logout(request)

        return HttpResponseRedirect(resolve_url(settings.LOGOUT_REDIRECT_URL))

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        """Fallback seguro redirecionando para login."""
        return HttpResponseRedirect(resolve_url(settings.LOGOUT_REDIRECT_URL))


class WorkspaceRedirectView(RequerAutenticacaoAdministrativaMixin, RedirectView):
    """Redireciona a raiz /painel/ para a tela principal de sites."""

    pattern_name = "painel:sites"
    permanent = False


class WorkspaceSitesView(RequerAutenticacaoAdministrativaMixin, TemplateView):
    """
    Workspace administrativo 'Meus Sites'.

    Exibe a listagem de projetos da plataforma. Nesta etapa (Prompt 2), renderiza
    o estado vazio limpo e profissional, preparando o layout para o Prompt 3.
    """

    template_name = "painel/sites/lista.html"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["titulo"] = "Meus Sites"
        # O modelo de sites/projetos será criado no Prompt 3; lista vazia inicialmente
        context["sites"] = []
        return context
