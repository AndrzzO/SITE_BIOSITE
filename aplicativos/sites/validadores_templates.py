"""Validação rigorosa de integridade e segurança para snapshots estruturais de templates e blocos."""

from typing import Any

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from .elementos import RegistroElementos
from .models import ContainerSite, SecaoSite, validar_cor_hex

SCHEMA_VERSIONS_SUPORTADAS = frozenset({1})
SCHEMA_VERSION_ATUAL = 1


def validar_elemento_snapshot(elemento_dict: dict[str, Any]) -> None:
    """Valida um elemento dentro de um snapshot contra o catálogo oficial."""
    if not isinstance(elemento_dict, dict):
        raise ValidationError(_("Cada elemento do snapshot deve ser um objeto JSON."))

    tipo = str(elemento_dict.get("tipo", "")).strip().lower()
    if not tipo:
        raise ValidationError(_("O campo 'tipo' do elemento é obrigatório no snapshot."))

    if not RegistroElementos.eh_valido(tipo):
        raise ValidationError(
            _("Tipo de elemento '%(tipo)s' não registrado ou não suportado pela plataforma."),
            params={"tipo": tipo},
        )

    definicao = RegistroElementos.obter(tipo)

    # Valida conteúdo
    conteudo = elemento_dict.get("conteudo", {})
    if not isinstance(conteudo, dict):
        raise ValidationError(
            _("O conteúdo do elemento '%(tipo)s' deve ser um objeto JSON."), params={"tipo": tipo}
        )
    definicao.validar_conteudo(conteudo)

    # Valida estilos se informados
    estilos = elemento_dict.get("estilos", {})
    if estilos:
        if not isinstance(estilos, dict):
            raise ValidationError(
                _("Os estilos do elemento '%(tipo)s' devem ser um objeto JSON."),
                params={"tipo": tipo},
            )
        definicao.validar_estilos(estilos)


def validar_container_snapshot(container_dict: dict[str, Any], profundidade: int = 1) -> None:
    """Valida recursivamente a estrutura de um container em snapshot."""
    if not isinstance(container_dict, dict):
        raise ValidationError(_("Cada container do snapshot deve ser um objeto JSON."))

    if profundidade > ContainerSite.MAX_PROFUNDIDADE:
        raise ValidationError(
            _("Profundidade máxima de aninhamento de %(max)d containers excedida no snapshot."),
            params={"max": ContainerSite.MAX_PROFUNDIDADE},
        )

    tipo_layout = container_dict.get("tipo_layout", "stack")
    if tipo_layout not in ContainerSite.TipoLayout.values:
        raise ValidationError(
            _("Tipo de layout '%(layout)s' inválido para container no snapshot."),
            params={"layout": tipo_layout},
        )

    elementos = container_dict.get("elementos", [])
    if not isinstance(elementos, list):
        raise ValidationError(_("A lista de elementos do container deve ser uma lista."))

    for elem in elementos:
        validar_elemento_snapshot(elem)

    filhos = container_dict.get("filhos", [])
    if not isinstance(filhos, list):
        raise ValidationError(_("A lista de containers filhos deve ser uma lista."))

    for filho in filhos:
        validar_container_snapshot(filho, profundidade=profundidade + 1)


def validar_secao_snapshot(secao_dict: dict[str, Any]) -> None:
    """Valida a estrutura de uma seção dentro de um snapshot."""
    if not isinstance(secao_dict, dict):
        raise ValidationError(_("A seção do snapshot deve ser um objeto JSON."))

    nome_interno = str(secao_dict.get("nome_interno", "")).strip()
    if not nome_interno:
        raise ValidationError(_("O campo 'nome_interno' da seção é obrigatório no snapshot."))

    tipo = secao_dict.get("tipo", "normal")
    if tipo not in SecaoSite.Tipo.values:
        raise ValidationError(
            _("Tipo de seção '%(tipo)s' inválido no snapshot."),
            params={"tipo": tipo},
        )

    containers = secao_dict.get("containers", [])
    if not isinstance(containers, list) or not containers:
        raise ValidationError(_("A seção no snapshot deve possuir pelo menos um container."))

    for c in containers:
        validar_container_snapshot(c, profundidade=1)


def validar_configuracao_visual_snapshot(config_dict: dict[str, Any]) -> None:
    """Valida os tokens de identidade visual presentes no snapshot."""
    if not isinstance(config_dict, dict):
        raise ValidationError(_("A configuração visual do snapshot deve ser um objeto JSON."))

    campos_cor = [
        "cor_primaria",
        "cor_secundaria",
        "cor_fundo",
        "cor_superficie",
        "cor_texto",
        "cor_texto_secundario",
    ]
    for campo in campos_cor:
        val = config_dict.get(campo)
        if val:
            validar_cor_hex(val)


def validar_snapshot_template(snapshot: dict[str, Any]) -> None:
    """
    Valida a integridade completa de um snapshot estrutural de TemplateSite.

    Garante schema_version compatível, configuração visual válida e árvore de
    páginas, seções, containers e elementos íntegra.
    """
    if not isinstance(snapshot, dict):
        raise ValidationError(_("O snapshot do template deve ser um objeto JSON."))

    versao = snapshot.get("schema_version")
    if versao not in SCHEMA_VERSIONS_SUPORTADAS:
        raise ValidationError(
            _("Versão de schema '%(versao)s' do template não suportada. Suportadas: %(sup)s."),
            params={"versao": versao, "sup": list(SCHEMA_VERSIONS_SUPORTADAS)},
        )

    if "configuracao_visual" in snapshot:
        validar_configuracao_visual_snapshot(snapshot["configuracao_visual"])

    paginas = snapshot.get("paginas")
    if not isinstance(paginas, list) or not paginas:
        raise ValidationError(_("O snapshot do template deve conter pelo menos uma página."))

    for pag in paginas:
        if not isinstance(pag, dict):
            raise ValidationError(_("Cada página do snapshot deve ser um objeto JSON."))
        titulo = str(pag.get("titulo", "")).strip()
        if not titulo:
            raise ValidationError(_("O campo 'titulo' da página é obrigatório no snapshot."))

        secoes = pag.get("secoes", [])
        if not isinstance(secoes, list) or not secoes:
            raise ValidationError(
                _("A página '%(pag)s' deve possuir pelo menos uma seção."), params={"pag": titulo}
            )

        for s in secoes:
            validar_secao_snapshot(s)


def validar_snapshot_bloco(snapshot: dict[str, Any]) -> None:
    """
    Valida a integridade de um snapshot estrutural de BlocoReutilizavel.

    Garante schema_version compatível e estrutura de seção com containers e elementos.
    """
    if not isinstance(snapshot, dict):
        raise ValidationError(_("O snapshot do bloco deve ser um objeto JSON."))

    versao = snapshot.get("schema_version")
    if versao not in SCHEMA_VERSIONS_SUPORTADAS:
        raise ValidationError(
            _("Versão de schema '%(versao)s' do bloco não suportada. Suportadas: %(sup)s."),
            params={"versao": versao, "sup": list(SCHEMA_VERSIONS_SUPORTADAS)},
        )

    secao = snapshot.get("secao")
    if not isinstance(secao, dict):
        raise ValidationError(
            _("O snapshot do bloco deve conter a chave 'secao' com uma seção válida.")
        )

    validar_secao_snapshot(secao)
