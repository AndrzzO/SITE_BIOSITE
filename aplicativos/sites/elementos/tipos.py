"""Definições dos tipos fundamentais de elementos do construtor."""

from typing import Any
from urllib.parse import urlparse

from django.core.exceptions import ValidationError
from django.utils.html import escape, format_html
from django.utils.translation import gettext_lazy as _

from .base import DefinicaoElemento
from .registry import registro_elementos


@registro_elementos.registrar
class ElementoTitulo(DefinicaoElemento):
    identificador = "titulo"
    nome = _("Título")
    categoria = _("Texto")
    icone = "🏷️"

    NIVEIS_PERMITIDOS = frozenset({"h1", "h2", "h3", "h4", "h5", "h6"})

    def conteudo_padrao(self) -> dict[str, Any]:
        return {
            "texto": "Título da Seção",
            "nivel": "h2",
        }

    def estilos_padrao(self) -> dict[str, Any]:
        return {
            "base": {
                "alinhamento": "center",
                "tamanho_fonte": 28,
                "peso_fonte": "bold",
            },
            "desktop": {
                "tamanho_fonte": 36,
            },
        }

    def validar_conteudo(self, conteudo: dict[str, Any]) -> None:
        if not isinstance(conteudo, dict):
            raise ValidationError(_("Conteúdo inválido para o elemento Título."))

        texto = conteudo.get("texto", "")
        if not isinstance(texto, str) or not texto.strip():
            raise ValidationError(_("O campo 'texto' do Título é obrigatório."))

        conteudo["texto"] = escape(texto)

        if len(conteudo["texto"]) > 300:
            raise ValidationError(_("O Título não pode exceder 300 caracteres."))

        nivel = conteudo.get("nivel", "h2")
        if nivel not in self.NIVEIS_PERMITIDOS:
            raise ValidationError(
                _("Nível de cabeçalho inválido: '%(nivel)s'."), params={"nivel": nivel}
            )

    def render(self, elemento: Any, contexto: dict[str, Any] | None = None) -> str:
        conteudo = elemento.conteudo or self.conteudo_padrao()
        nivel = conteudo.get("nivel", "h2")
        texto = conteudo.get("texto", "")
        return format_html('<{0} class="elemento-titulo">{1}</{0}>', nivel, texto)


@registro_elementos.registrar
class ElementoTexto(DefinicaoElemento):
    identificador = "texto"
    nome = _("Parágrafo")
    categoria = _("Texto")
    icone = "📝"

    def conteudo_padrao(self) -> dict[str, Any]:
        return {
            "texto": "Escreva seu texto aqui...",
        }

    def estilos_padrao(self) -> dict[str, Any]:
        return {
            "base": {
                "alinhamento": "left",
                "tamanho_fonte": 16,
            },
            "desktop": {},
        }

    def validar_conteudo(self, conteudo: dict[str, Any]) -> None:
        if not isinstance(conteudo, dict):
            raise ValidationError(_("Conteúdo inválido para o elemento Texto."))

        texto = conteudo.get("texto", "")
        if not isinstance(texto, str) or not texto.strip():
            raise ValidationError(_("O campo 'texto' do Parágrafo é obrigatório."))

        conteudo["texto"] = escape(texto)

    def render(self, elemento: Any, contexto: dict[str, Any] | None = None) -> str:
        conteudo = elemento.conteudo or self.conteudo_padrao()
        texto = conteudo.get("texto", "")
        return format_html('<p class="elemento-texto">{}</p>', texto)


@registro_elementos.registrar
class ElementoBotao(DefinicaoElemento):
    identificador = "botao"
    nome = _("Botão de Ação")
    categoria = _("Ação")
    icone = "🔘"

    PROTOCOLOS_PERMITIDOS = frozenset({"http", "https", "mailto", "tel", "whatsapp", "sms"})

    def conteudo_padrao(self) -> dict[str, Any]:
        return {
            "texto": "Clique Aqui",
            "url": "https://",
            "nova_aba": True,
        }

    def estilos_padrao(self) -> dict[str, Any]:
        return {
            "base": {
                "alinhamento": "center",
                "tamanho_fonte": 16,
                "cor_fundo": "#2563eb",
                "cor_texto": "#ffffff",
                "raio_borda": 8,
                "padding_topo": 12,
                "padding_baixo": 12,
            },
            "desktop": {},
        }

    def validar_conteudo(self, conteudo: dict[str, Any]) -> None:
        if not isinstance(conteudo, dict):
            raise ValidationError(_("Conteúdo inválido para o elemento Botão."))

        texto = conteudo.get("texto", "").strip()
        if not texto:
            raise ValidationError(_("O texto do botão é obrigatório."))

        if len(texto) > 100:
            raise ValidationError(_("O texto do botão não pode exceder 100 caracteres."))

        url = conteudo.get("url", "").strip()
        if url:
            url_lower = url.lower()
            if url_lower.startswith(("javascript:", "data:", "vbscript:")):
                raise ValidationError(
                    _(
                        "Protocolo de URL não permitido: 'javascript:' ou protocolos perigosos são proibidos por segurança."
                    )
                )

            if not url_lower.startswith("/"):
                parsed = urlparse(url)
                if parsed.scheme and parsed.scheme.lower() not in self.PROTOCOLOS_PERMITIDOS:
                    raise ValidationError(
                        _("Protocolo de URL não permitido ou não seguro: '%(scheme)s'."),
                        params={"scheme": parsed.scheme},
                    )

    def render(self, elemento: Any, contexto: dict[str, Any] | None = None) -> str:
        conteudo = elemento.conteudo or self.conteudo_padrao()
        texto = escape(conteudo.get("texto", ""))
        url = escape(conteudo.get("url", "#"))
        target = (
            ' target="_blank" rel="noopener noreferrer"' if conteudo.get("nova_aba", True) else ""
        )
        return format_html('<a href="{}" class="elemento-botao"{}>{}</a>', url, target, texto)


@registro_elementos.registrar
class ElementoImagem(DefinicaoElemento):
    identificador = "imagem"
    nome = _("Imagem")
    categoria = _("Mídia")
    icone = "🖼️"

    def conteudo_padrao(self) -> dict[str, Any]:
        return {
            "url": "",
            "alt_text": "Imagem ilustrativa",
        }

    def validar_conteudo(self, conteudo: dict[str, Any]) -> None:
        if not isinstance(conteudo, dict):
            raise ValidationError(_("Conteúdo inválido para o elemento Imagem."))

        url = conteudo.get("url", "")
        if url and isinstance(url, str):
            if url.lower().startswith("javascript:"):
                raise ValidationError(_("URL não permitida para imagem."))

        alt_text = conteudo.get("alt_text", "")
        if alt_text and len(str(alt_text)) > 200:
            raise ValidationError(_("Texto alternativo não pode exceder 200 caracteres."))

    def render(self, elemento: Any, contexto: dict[str, Any] | None = None) -> str:
        conteudo = elemento.conteudo or self.conteudo_padrao()
        url = escape(conteudo.get("url", ""))
        alt = escape(conteudo.get("alt_text", ""))
        if not url:
            return format_html(
                '<div class="imagem-placeholder" aria-label="{}">🖼️ Imagem</div>', alt
            )
        return format_html(
            '<img src="{}" alt="{}" class="elemento-imagem" loading="lazy">', url, alt
        )


@registro_elementos.registrar
class ElementoEspacador(DefinicaoElemento):
    identificador = "espacador"
    nome = _("Espaçador")
    categoria = _("Layout")
    icone = "↕️"

    def conteudo_padrao(self) -> dict[str, Any]:
        return {
            "altura": 24,
        }

    def validar_conteudo(self, conteudo: dict[str, Any]) -> None:
        if not isinstance(conteudo, dict):
            raise ValidationError(_("Conteúdo inválido para Espaçador."))

        altura = conteudo.get("altura", 24)
        if not isinstance(altura, (int, float)) or altura < 4 or altura > 300:
            raise ValidationError(_("A altura do espaçador deve ser entre 4px e 300px."))

    def render(self, elemento: Any, contexto: dict[str, Any] | None = None) -> str:
        conteudo = elemento.conteudo or self.conteudo_padrao()
        altura = int(conteudo.get("altura", 24))
        return format_html(
            '<div class="elemento-espacador" style="height: {}px;" aria-hidden="true"></div>',
            altura,
        )


@registro_elementos.registrar
class ElementoIcone(DefinicaoElemento):
    identificador = "icone"
    nome = _("Ícone")
    categoria = _("Mídia")
    icone = "⭐"

    def conteudo_padrao(self) -> dict[str, Any]:
        return {
            "icone": "star",
        }

    def validar_conteudo(self, conteudo: dict[str, Any]) -> None:
        if not isinstance(conteudo, dict):
            raise ValidationError(_("Conteúdo inválido para Ícone."))

        icone = conteudo.get("icone", "").strip()
        if not icone:
            raise ValidationError(_("O identificador do ícone é obrigatório."))

        if len(icone) > 50:
            raise ValidationError(_("Identificador de ícone muito longo."))

    def render(self, elemento: Any, contexto: dict[str, Any] | None = None) -> str:
        conteudo = elemento.conteudo or self.conteudo_padrao()
        icone = escape(conteudo.get("icone", "star"))
        return format_html('<span class="elemento-icone" aria-hidden="true">{}</span>', icone)
