"""
Views administrativas privadas para gerenciamento de Links Inteligentes, Tags NFC e QR Codes (Prompt 10).
"""

import logging
from typing import Any

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import models
from django.http import (
    Http404,
    HttpRequest,
    HttpResponse,
)
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic import ListView

from aplicativos.administracao.permissoes import RequerAutenticacaoAdministrativaMixin

from .models import LinkInteligente, ProjetoSite
from .servicos_links import (
    alterar_vinculo_projeto,
    alternar_status_link,
    criar_link_inteligente,
    obter_url_completa_link,
)
from .servicos_qrcode import TAMANHOS_PERMITIDOS_QR, gerar_imagem_qrcode

logger = logging.getLogger("aplicativos.sites.views_links")


class LinksInteligentesGlobalListView(RequerAutenticacaoAdministrativaMixin, ListView):
    """
    Listagem administrativa global de todos os Links Inteligentes (NFC e QR Code).
    Suporta busca textual, filtros por tipo/status e paginação eficiente sem N+1.
    """

    model = LinkInteligente
    template_name = "painel/links/lista.html"
    context_object_name = "links"
    paginate_by = 20

    def get_queryset(self):
        qs = (
            LinkInteligente.objects.select_related("projeto", "projeto__cliente")
            .prefetch_related("historico_vinculos")
            .order_by("-criado_em")
        )

        termo = self.request.GET.get("q", "").strip()
        if termo:
            qs = qs.filter(
                models.Q(nome__icontains=termo)
                | models.Q(token__icontains=termo)
                | models.Q(projeto__nome__icontains=termo)
                | models.Q(projeto__slug__icontains=termo)
                | models.Q(projeto__cliente__nome__icontains=termo)
            )

        tipo = self.request.GET.get("tipo", "").strip().lower()
        if tipo in (LinkInteligente.Tipo.NFC, LinkInteligente.Tipo.QR, LinkInteligente.Tipo.CURTO):
            qs = qs.filter(tipo=tipo)

        status = self.request.GET.get("status", "").strip().lower()
        if status in (LinkInteligente.Status.ATIVO, LinkInteligente.Status.INATIVO):
            qs = qs.filter(status=status)

        return qs

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["titulo"] = "Links Inteligentes (NFC & QR Code)"
        context["q"] = self.request.GET.get("q", "")
        context["tipo_atual"] = self.request.GET.get("tipo", "")
        context["status_atual"] = self.request.GET.get("status", "")
        context["total_geral"] = LinkInteligente.objects.count()
        context["total_nfc"] = LinkInteligente.objects.filter(tipo=LinkInteligente.Tipo.NFC).count()
        context["total_qr"] = LinkInteligente.objects.filter(tipo=LinkInteligente.Tipo.QR).count()
        context["projetos_disponiveis"] = ProjetoSite.objects.exclude(
            status=ProjetoSite.Status.ARQUIVADO
        ).order_by("nome")
        return context


class LinkInteligenteCriarView(RequerAutenticacaoAdministrativaMixin, View):
    """Criação rápida de uma Tag NFC ou QR Code vinculada a um ProjetoSite."""

    def post(self, request: HttpRequest, uuid: str) -> HttpResponse:
        projeto = get_object_or_404(ProjetoSite, uuid=uuid)

        tipo = request.POST.get("tipo", LinkInteligente.Tipo.NFC).strip().lower()
        if tipo not in (
            LinkInteligente.Tipo.NFC,
            LinkInteligente.Tipo.QR,
            LinkInteligente.Tipo.CURTO,
        ):
            tipo = LinkInteligente.Tipo.NFC

        nome = request.POST.get("nome", "").strip()
        descricao = request.POST.get("descricao", "").strip()
        tipo_midia = request.POST.get(
            "tipo_midia_fisica", LinkInteligente.TipoMidiaFisica.CARTAO
        ).strip()

        try:
            link = criar_link_inteligente(
                projeto=projeto,
                tipo=tipo,
                nome=nome,
                descricao=descricao,
                tipo_midia_fisica=tipo_midia,
                usuario=request.user,
            )
            url_publica = obter_url_completa_link(link, request=request)
            tipo_label = "Tag NFC" if tipo == LinkInteligente.Tipo.NFC else "QR Code"
            messages.success(
                request,
                f"{tipo_label} '{link.nome}' criada com sucesso! URL estável: {url_publica}",
            )
        except Exception as e:
            logger.exception("Erro ao criar link inteligente para o projeto %s: %s", projeto.id, e)
            messages.error(request, f"Erro ao criar link inteligente: {e}")

        # Redireciona de volta para a aba de links no detalhe do projeto ou para a listagem
        origem = request.POST.get("next", "")
        if origem:
            return redirect(origem)
        return redirect("painel:site_detalhe", uuid=projeto.uuid)


class LinkInteligenteAlternarStatusView(RequerAutenticacaoAdministrativaMixin, View):
    """Ativa ou desativa operacionalmente um link inteligente."""

    def post(self, request: HttpRequest, uuid: str) -> HttpResponse:
        link = get_object_or_404(LinkInteligente, uuid=uuid)
        acao = request.POST.get("acao", "").strip().lower()

        if acao == "ativar":
            alternar_status_link(link, ativar=True)
            messages.success(request, f"Link '{link.nome}' ativado com sucesso!")
        elif acao == "desativar":
            alternar_status_link(link, ativar=False)
            messages.warning(
                request, f"Link '{link.nome}' desativado. Ele não redirecionará visitantes."
            )
        else:
            # Alternância simples
            novo_estado = not (link.status == LinkInteligente.Status.ATIVO)
            alternar_status_link(link, ativar=novo_estado)
            msg = "ativado" if novo_estado else "desativado"
            messages.success(request, f"Link '{link.nome}' {msg} com sucesso.")

        origem = request.POST.get("next", "")
        if origem:
            return redirect(origem)
        return redirect("painel:site_detalhe", uuid=link.projeto.uuid)


class LinkInteligenteAlterarDestinoView(RequerAutenticacaoAdministrativaMixin, View):
    """Altera o projeto vinculado à tag com registro de auditoria imutável."""

    def post(self, request: HttpRequest, uuid: str) -> HttpResponse:
        link = get_object_or_404(LinkInteligente, uuid=uuid)
        novo_projeto_uuid = request.POST.get("novo_projeto_uuid", "").strip()
        motivo = request.POST.get("motivo", "").strip()

        if not novo_projeto_uuid:
            messages.error(request, "Por favor, selecione o novo projeto de destino.")
            return redirect("painel:site_detalhe", uuid=link.projeto.uuid)

        novo_projeto = get_object_or_404(ProjetoSite, uuid=novo_projeto_uuid)

        try:
            alterar_vinculo_projeto(
                link=link,
                novo_projeto=novo_projeto,
                usuario=request.user,
                motivo=motivo,
            )
            messages.success(
                request,
                f"Destino da tag '{link.nome}' alterado para '{novo_projeto.nome}' com sucesso!",
            )
        except Exception as e:
            logger.exception("Erro ao alterar vínculo do link %s: %s", link.id, e)
            messages.error(request, f"Erro ao alterar vínculo: {e}")

        origem = request.POST.get("next", "")
        if origem:
            return redirect(origem)
        return redirect("painel:site_detalhe", uuid=novo_projeto.uuid)


class LinkInteligenteQrDownloadView(RequerAutenticacaoAdministrativaMixin, View):
    """Visualização e download de imagem de QR Code em alta resolução (PNG)."""

    def get(self, request: HttpRequest, uuid: str) -> HttpResponse:
        link = get_object_or_404(LinkInteligente, uuid=uuid)

        try:
            tamanho = int(request.GET.get("tamanho", 512))
        except (ValueError, TypeError):
            tamanho = 512

        if tamanho not in TAMANHOS_PERMITIDOS_QR:
            tamanho = 512

        try:
            png_bytes = gerar_imagem_qrcode(
                link=link,
                tamanho=tamanho,
                request=request,
            )
        except ValidationError as e:
            raise Http404(str(e)) from e

        response = HttpResponse(png_bytes, content_type="image/png")

        deve_baixar = request.GET.get("download", "0") in ("1", "true", "True")
        if deve_baixar:
            slug_projeto = link.projeto.slug
            filename = f"qrcode-{slug_projeto}-{link.token[:6]}.png"
            response["Content-Disposition"] = f'attachment; filename="{filename}"'

        return response
