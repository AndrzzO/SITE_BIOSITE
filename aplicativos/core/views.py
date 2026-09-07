"""Views centrais e operacionais do sistema."""

from django.http import HttpRequest, JsonResponse
from django.views.generic import TemplateView


def health_check(request: HttpRequest) -> JsonResponse:
    """
    Endpoint operacional simples para verificação de liveness do serviço.

    Não revela detalhes internos de arquitetura, banco, versões ou segredos.
    """
    return JsonResponse(
        {"status": "ok"},
        status=200,
    )


class HomeView(TemplateView):
    """
    Página inicial temporária indicando status operacional da plataforma.

    Não antecipa a criação do site institucional ou das páginas públicas de BioSites.
    """

    template_name = "core/index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["titulo"] = "Plataforma BioSite NFC"
        context["status"] = "Fundação Operacional"
        return context
