"""Classe base abstrata para definições de tipos de elementos."""

import re
from abc import ABC, abstractmethod
from typing import Any

from django.core.exceptions import ValidationError
from django.utils.html import escape
from django.utils.translation import gettext_lazy as _

HEX_COLOR_REGEX = re.compile(r"^#(?:[0-9a-fA-F]{3}){1,2}$")


class DefinicaoElemento(ABC):
    """
    Especificação formal de um tipo de elemento estrutural da plataforma.

    Cada tipo define:
    - Metadados administrativos (nome, ícone, categoria).
    - Valores padrão de conteúdo, estilo e configuração.
    - Validadores rigorosos de schema para prevenir corrupção de dados ou ataques XSS.
    - Renderização segura para HTML.
    """

    identificador: str
    nome: str
    categoria: str = "Geral"
    icone: str = "📦"
    rastreavel: bool = False
    categoria_analytics: str = ""
    rotulo_analytics: str = ""

    PROPRIEDADES_ESTILO_PERMITIDAS = frozenset(
        {
            # Nomes em Português
            "alinhamento",
            "tamanho_fonte",
            "peso_fonte",
            "cor_texto",
            "cor_fundo",
            "cor_borda",
            "largura_borda",
            "estilo_borda",
            "raio_borda",
            "sombra",
            "margem_topo",
            "margem_baixo",
            "padding_topo",
            "padding_baixo",
            "padding_lateral",
            "opacidade",
            "largura_maxima",
            "gap",
            "animacao",
            "backdrop_filter",
            # Nomes CSS equivalentes
            "text-align",
            "font-size",
            "font-weight",
            "color",
            "background-color",
            "border-color",
            "border-width",
            "border-style",
            "border-radius",
            "box-shadow",
            "margin-top",
            "margin-bottom",
            "padding-top",
            "padding-bottom",
            "padding-left",
            "padding-right",
            "opacity",
            "max-width",
            "animation",
            "backdrop-filter",
        }
    )

    ALINHAMENTOS_PERMITIDOS = frozenset({"left", "center", "right", "justify"})
    PESOS_FONTE_PERMITIDOS = frozenset(
        {"normal", "bold", "300", "400", "500", "600", "700", "800", "900"}
    )
    ESTILOS_BORDA_PERMITIDOS = frozenset({"none", "solid", "dashed", "dotted"})
    SOMBRAS_PERMITIDAS = frozenset({"none", "suave", "media", "forte", "glow"})
    ANIMACOES_PERMITIDAS = frozenset({"none", "fade", "fade-up", "scale", "slide"})

    @abstractmethod
    def conteudo_padrao(self) -> dict[str, Any]:
        """Retorna o dicionário padrão de conteúdo do elemento."""
        ...

    def obter_conteudo_padrao(self) -> dict[str, Any]:
        """Alias conveniente para conteudo_padrao."""
        return self.conteudo_padrao()

    def estilos_padrao(self) -> dict[str, Any]:
        """
        Retorna os estilos padrão do elemento segundo a arquitetura Mobile-First.

        'base': estilos aplicados a smartphones (390px).
        'desktop': overrides opcionais para telas amplas.
        """
        return {
            "base": {
                "alinhamento": "left",
            },
            "desktop": {},
        }

    def configuracao_padrao(self) -> dict[str, Any]:
        """Retorna parâmetros adicionais específicos do elemento."""
        return {}

    def obter_token_clique(
        self,
        elemento: Any,
        contexto: dict[str, Any] | None = None,
        subitem_id: str | None = None,
    ) -> str:
        """
        Retorna o atributo HTML data-event-token se o elemento for rastreável (Prompt 11)
        e o contexto fornecer a função de assinatura de tokens analíticos.
        """
        if not self.rastreavel or not contexto:
            return ""
        gerador = contexto.get("gerar_token_clique")
        if not callable(gerador):
            return ""
        elem_id = getattr(elemento, "id", None) or getattr(elemento, "uuid", "")
        token = gerador(self.identificador.upper(), elem_id, subitem_id)
        return f' data-event-token="{escape(token)}"' if token else ""

    @abstractmethod
    def validar_conteudo(self, conteudo: dict[str, Any]) -> None:
        """Valida se o conteúdo respeita o schema obrigatório do tipo."""
        ...

    def validar_estilos(self, estilos: dict[str, Any]) -> None:
        """
        Valida a estrutura de estilos do elemento.

        Garante que apenas propriedades permitidas da allowlist sejam utilizadas,
        com valores numéricos e formatos de cores verificados.
        """
        if not isinstance(estilos, dict):
            raise ValidationError(_("O campo de estilos deve ser um objeto JSON."))

        for escopo in ["base", "desktop"]:
            regras = estilos.get(escopo, {})
            if not isinstance(regras, dict):
                continue

            for prop, valor in regras.items():
                if prop not in self.PROPRIEDADES_ESTILO_PERMITIDAS:
                    raise ValidationError(
                        _("Propriedade de estilo não permitida: '%(prop)s'."),
                        params={"prop": prop},
                    )

                if (
                    prop in ["alinhamento", "text-align"]
                    and valor not in self.ALINHAMENTOS_PERMITIDOS
                ):
                    raise ValidationError(
                        _("Alinhamento inválido: '%(valor)s'."), params={"valor": valor}
                    )

                if (
                    prop in ["peso_fonte", "font-weight"]
                    and str(valor) not in self.PESOS_FONTE_PERMITIDOS
                ):
                    raise ValidationError(
                        _("Peso de fonte inválido: '%(valor)s'."), params={"valor": valor}
                    )

                if (
                    prop
                    in [
                        "cor_texto",
                        "cor_fundo",
                        "cor_borda",
                        "color",
                        "background-color",
                        "border-color",
                    ]
                    and valor
                ):
                    if not HEX_COLOR_REGEX.match(str(valor)):
                        raise ValidationError(
                            _("Cor hexadecimal inválida: '%(valor)s'."), params={"valor": valor}
                        )

                if (
                    prop in ["estilo_borda", "border-style"]
                    and valor not in self.ESTILOS_BORDA_PERMITIDOS
                ):
                    raise ValidationError(
                        _("Estilo de borda inválido: '%(valor)s'."), params={"valor": valor}
                    )

                if (
                    prop in ["sombra", "box-shadow"]
                    and str(valor).lower() not in self.SOMBRAS_PERMITIDAS
                ):
                    raise ValidationError(
                        _("Preset de sombra inválido: '%(valor)s'."), params={"valor": valor}
                    )

                if (
                    prop in ["animacao", "animation"]
                    and str(valor).lower() not in self.ANIMACOES_PERMITIDAS
                ):
                    raise ValidationError(
                        _("Preset de animação inválido: '%(valor)s'."), params={"valor": valor}
                    )

                if prop in [
                    "tamanho_fonte",
                    "margem_topo",
                    "margem_baixo",
                    "padding_topo",
                    "padding_baixo",
                    "raio_borda",
                    "font-size",
                    "margin-top",
                    "margin-bottom",
                    "padding-top",
                    "padding-bottom",
                    "border-radius",
                ]:
                    val_num = valor
                    if isinstance(valor, str) and valor.endswith("px"):
                        try:
                            val_num = float(valor[:-2])
                        except ValueError as err:
                            raise ValidationError(
                                _("Dimensão inválida para '%(prop)s'."), params={"prop": prop}
                            ) from err

                    if not isinstance(val_num, (int, float)) or val_num < 0 or val_num > 500:
                        raise ValidationError(
                            _("Dimensão inválida para '%(prop)s'."), params={"prop": prop}
                        )

    @abstractmethod
    def render(self, elemento: Any, contexto: dict[str, Any] | None = None) -> str:
        """Renderiza o elemento em HTML seguro."""
        ...


def calcular_luminancia_relativa(hex_cor: str) -> float:
    """Calcula a luminância relativa (0.0 a 1.0) conforme a especificação WCAG 2.1."""
    if not hex_cor:
        return 0.5
    hex_clean = hex_cor.strip().lstrip("#")
    if len(hex_clean) == 3:
        hex_clean = "".join(c * 2 for c in hex_clean)
    if len(hex_clean) != 6:
        return 0.5
    try:
        r = int(hex_clean[0:2], 16) / 255.0
        g = int(hex_clean[2:4], 16) / 255.0
        b = int(hex_clean[4:6], 16) / 255.0
    except ValueError:
        return 0.5

    def _ajustar(c: float) -> float:
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    return 0.2126 * _ajustar(r) + 0.7152 * _ajustar(g) + 0.0722 * _ajustar(b)


def calcular_contraste_wcag(cor_texto_hex: str, cor_fundo_hex: str) -> dict[str, Any]:
    """
    Calcula a taxa de contraste (1:1 a 21:1) entre texto e fundo.
    Retorna proporção e flags de conformidade WCAG AA.
    """
    lum1 = calcular_luminancia_relativa(cor_texto_hex)
    lum2 = calcular_luminancia_relativa(cor_fundo_hex)
    mais_clara = max(lum1, lum2)
    mais_escura = min(lum1, lum2)
    ratio = (mais_clara + 0.05) / (mais_escura + 0.05)
    ratio_formatado = round(ratio, 2)
    return {
        "ratio": ratio_formatado,
        "adequado_texto_normal": ratio >= 4.5,
        "adequado_texto_grande": ratio >= 3.0,
        "alerta": ratio < 3.0,
    }
