"""Registro centralizado e desacoplado de tipos de elementos."""

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from .base import DefinicaoElemento


class RegistroElementos:
    """
    Registro singleton para catálogo de tipos de elementos.

    Evita blocos if/elif gigantescos pelo sistema, centralizando schemas,
    comportamentos e validações. Pode ser invocado tanto como classe
    quanto através da instância singleton 'registro_elementos'.
    """

    _elementos: dict[str, DefinicaoElemento] = {}

    @classmethod
    def registrar(cls, classe_elemento: type[DefinicaoElemento]) -> type[DefinicaoElemento]:
        """Registra uma nova definição de elemento."""
        instancia = classe_elemento()
        identificador = instancia.identificador.strip().lower()
        cls._elementos[identificador] = instancia
        return classe_elemento

    @classmethod
    def obter(cls, identificador: str) -> DefinicaoElemento:
        """Obtém a definição do elemento pelo seu identificador único."""
        chave = identificador.strip().lower() if identificador else ""
        if chave not in cls._elementos:
            raise ValidationError(
                _("Tipo de elemento não suportado ou não registrado: '%(tipo)s'."),
                params={"tipo": identificador},
            )
        return cls._elementos[chave]

    @classmethod
    def eh_valido(cls, identificador: str) -> bool:
        """Verifica se o tipo está registrado."""
        chave = identificador.strip().lower() if identificador else ""
        return chave in cls._elementos

    @classmethod
    def listar_tipos(cls) -> list[dict[str, str]]:
        """Retorna a lista de tipos registrados com metadados para formulários e editor."""
        return [
            {
                "identificador": elem.identificador,
                "nome": elem.nome,
                "categoria": elem.categoria,
                "icone": elem.icone,
            }
            for elem in cls._elementos.values()
        ]

    @classmethod
    def choices(cls) -> list[tuple[str, str]]:
        """Retorna tuplas para uso em choices do Django model/form."""
        return [(elem.identificador, elem.nome) for elem in cls._elementos.values()]

    @classmethod
    def obter_tipos_registrados(cls) -> dict[str, DefinicaoElemento]:
        """Retorna dicionário com todos os elementos registrados em maiúsculas."""
        return {k.upper(): v for k, v in cls._elementos.items()}


# Instância global compartilhada do registro
registro_elementos = RegistroElementos()
