"""Views centrais e operacionais do sistema."""

import logging
from typing import Any

from django.contrib.auth import login as auth_login
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect, JsonResponse
from django.urls import reverse_lazy
from django.views.generic import FormView

from aplicativos.administracao.forms import AutenticacaoAdministrativaForm
from aplicativos.administracao.servicos.rate_limit import ServicoRateLimitLogin

logger = logging.getLogger("aplicativos.core.views")


def health_check(request: HttpRequest) -> JsonResponse:
    """
    Endpoint operacional simples para verificação de liveness do serviço.

    Não revela detalhes internos de arquitetura, banco, versões ou segredos.
    """
    return JsonResponse(
        {"status": "ok"},
        status=200,
    )


class HomeView(FormView):
    """
    Página inicial da plataforma BioSite NFC com status operacional e acesso direto por login.
    """

    template_name = "core/index.html"
    form_class = AutenticacaoAdministrativaForm
    success_url = reverse_lazy("painel:sites")

    def get_form_kwargs(self) -> dict[str, Any]:
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs

    def form_valid(self, form: AutenticacaoAdministrativaForm) -> HttpResponse:
        user = form.get_user()
        auth_login(self.request, user)

        ip = ServicoRateLimitLogin.obter_ip_cliente(self.request)
        ServicoRateLimitLogin.limpar_falhas(ip, form.cleaned_data.get("identificador", ""))
        logger.info(
            "Login via Home realizado com sucesso para o usuário '%s' a partir do IP %s",
            user.username,
            ip,
        )
        return HttpResponseRedirect(self.get_success_url())

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["titulo"] = "Plataforma BioSite NFC"
        context["status"] = "Fundação Operacional"
        return context
