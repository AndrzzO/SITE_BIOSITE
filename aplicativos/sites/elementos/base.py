"""Classe base abstrata para definições de tipos de elementos."""

import re
from abc import ABC, abstractmethod
from typing import Any

from django.core.exceptions import ValidationError
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
            "raio_borda",
            "margem_topo",
            "margem_baixo",
            "padding_topo",
            "padding_baixo",
            "padding_lateral",
            "opacidade",
            # Nomes CSS equivalentes
            "text-align",
            "font-size",
            "font-weight",
            "color",
            "background-color",
            "border-color",
            "border-width",
            "border-radius",
            "margin-top",
            "margin-bottom",
            "padding-top",
            "padding-bottom",
            "padding-left",
            "padding-right",
            "opacity",
        }
    )

    ALINHAMENTOS_PERMITIDOS = frozenset({"left", "center", "right", "justify"})
    PESOS_FONTE_PERMITIDOS = frozenset(
        {"normal", "bold", "300", "400", "500", "600", "700", "800", "900"}
    )

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
