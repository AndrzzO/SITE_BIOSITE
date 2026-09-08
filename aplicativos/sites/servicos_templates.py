"""Serviços de serialização, sanitização, instanciação e clonagem de Templates e Blocos."""

import copy
import logging
from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Max
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from aplicativos.clientes.models import Cliente

from .elementos import RegistroElementos
from .models import (
    BlocoReutilizavel,
    ContainerSite,
    ElementoSite,
    PaginaSite,
    ProjetoSite,
    SecaoSite,
    TemplateSite,
    garantir_configuracao_visual,
)
from .servicos import gerar_slug_unico
from .validadores_templates import (
    SCHEMA_VERSION_ATUAL,
    validar_snapshot_bloco,
    validar_snapshot_template,
)

logger = logging.getLogger("aplicativos.sites.servicos_templates")

# Placeholders profissionais padrão para sanitização segura
PLACEHOLDERS = {
    "nome": "Seu Nome Completo",
    "profissao": "Sua Profissão ou Especialidade",
    "bio": "Apresente aqui uma breve descrição sobre você, seu trabalho e seus diferenciais de atendimento.",
    "whatsapp_num": "5511999999999",
    "whatsapp_msg": "Olá! Gostaria de mais informações sobre seus serviços.",
    "telefone": "(11) 99999-9999",
    "email": "contato@meubiosite.com",
    "website": "https://meubiosite.com.br",
    "endereco": "Av. Paulista, 1000 - Bela Vista, São Paulo - SP",
}


def sanitizar_elemento_para_template(elemento_dict: dict[str, Any]) -> dict[str, Any]:
    """
    Substitui dados particulares de clientes por placeholders genéricos profissionais.

    Garante que nomes pessoais, telefones, números de WhatsApp reais e links
    particulares de clientes não vazem em templates reutilizáveis.
    """
    elem_copia = copy.deepcopy(elemento_dict)
    tipo = str(elem_copia.get("tipo", "")).lower()
    conteudo = elem_copia.get("conteudo", {})

    if tipo == "whatsapp":
        conteudo["numero"] = PLACEHOLDERS["whatsapp_num"]
        conteudo["mensagem"] = PLACEHOLDERS["whatsapp_msg"]
    elif tipo == "telefone":
        conteudo["numero"] = PLACEHOLDERS["telefone"]
    elif tipo == "email":
        conteudo["email"] = PLACEHOLDERS["email"]
    elif tipo == "website":
        conteudo["url"] = PLACEHOLDERS["website"]
    elif tipo == "mapa":
        conteudo["endereco"] = PLACEHOLDERS["endereco"]
        conteudo["url_personalizada"] = ""
    elif tipo == "avatar":
        # Remove caminho específico de arquivo privado para usar placeholder
        conteudo["url"] = ""
    elif tipo == "imagem":
        conteudo["url"] = ""
    elif tipo == "galeria":
        # Converte imagens de clientes para placeholders
        imagens = conteudo.get("imagens", [])
        for idx, img in enumerate(imagens):
            img["url"] = ""
            img["alt"] = f"Foto {idx + 1}"

    elem_copia["conteudo"] = conteudo
    return elem_copia


def _serializar_container_recursivo(
    container: ContainerSite, substituir_placeholders: bool
) -> dict[str, Any]:
    elementos_serializados = []
    for elem in container.elementos.filter(ativo=True).order_by("ordem"):
        item = {
            "tipo": elem.tipo.lower(),
            "conteudo": copy.deepcopy(elem.conteudo),
            "estilos": copy.deepcopy(elem.estilos),
            "configuracao": copy.deepcopy(elem.configuracao),
        }
        if substituir_placeholders:
            item = sanitizar_elemento_para_template(item)
        elementos_serializados.append(item)

    filhos_serializados = [
        _serializar_container_recursivo(filho, substituir_placeholders)
        for filho in container.filhos.filter(ativo=True).order_by("ordem")
    ]

    return {
        "tipo_layout": container.tipo_layout,
        "estilos": copy.deepcopy(container.estilos),
        "configuracao": copy.deepcopy(container.configuracao),
        "elementos": elementos_serializados,
        "filhos": filhos_serializados,
    }


def serializar_secao_para_snapshot(
    secao: SecaoSite, substituir_placeholders: bool = True
) -> dict[str, Any]:
    """Serializa uma seção em um snapshot estruturado pronto para BlocoReutilizavel."""
    containers_raiz = secao.containers.filter(parent__isnull=True, ativo=True).order_by("ordem")
    containers_serializados = [
        _serializar_container_recursivo(c, substituir_placeholders) for c in containers_raiz
    ]

    return {
        "schema_version": SCHEMA_VERSION_ATUAL,
        "secao": {
            "nome_interno": secao.nome_interno,
            "tipo": secao.tipo,
            "estilos": copy.deepcopy(secao.estilos),
            "configuracao": copy.deepcopy(secao.configuracao),
            "containers": containers_serializados,
        },
    }


def serializar_projeto_para_snapshot(
    projeto: ProjetoSite, substituir_placeholders: bool = True
) -> dict[str, Any]:
    """Serializa um projeto completo em um snapshot estruturado pronto para TemplateSite."""
    config_visual = getattr(projeto, "configuracao_visual", None)
    if not config_visual:
        config_visual = garantir_configuracao_visual(projeto)

    config_dict = {
        "cor_primaria": config_visual.cor_primaria,
        "cor_secundaria": config_visual.cor_secundaria,
        "cor_fundo": config_visual.cor_fundo,
        "cor_superficie": config_visual.cor_superficie,
        "cor_texto": config_visual.cor_texto,
        "cor_texto_secundario": config_visual.cor_texto_secundario,
        "fonte_principal": config_visual.fonte_principal,
        "fonte_titulos": config_visual.fonte_titulos,
        "radius_padrao": config_visual.radius_padrao,
        "sombra_padrao": config_visual.sombra_padrao,
        "largura_maxima_mobile": config_visual.largura_maxima_mobile,
    }

    paginas_serializadas = []
    for pag in projeto.paginas.filter(ativa=True).order_by("ordem"):
        secoes_serializadas = []
        for s in pag.secoes.filter(ativa=True).order_by("ordem"):
            snap_s = serializar_secao_para_snapshot(s, substituir_placeholders)
            secoes_serializadas.append(snap_s["secao"])

        paginas_serializadas.append(
            {
                "titulo": pag.titulo,
                "slug": pag.slug,
                "eh_inicial": pag.eh_inicial,
                "secoes": secoes_serializadas,
            }
        )

    return {
        "schema_version": SCHEMA_VERSION_ATUAL,
        "configuracao_visual": config_dict,
        "paginas": paginas_serializadas,
    }


def _instanciar_containers_recursivo(
    containers_lista: list[dict[str, Any]],
    nova_secao: SecaoSite,
    parent_container: ContainerSite | None = None,
) -> None:
    for idx_c, c_dict in enumerate(containers_lista):
        novo_c = ContainerSite.objects.create(
            secao=nova_secao,
            parent=parent_container,
            tipo_layout=c_dict.get("tipo_layout", "stack"),
            ordem=(idx_c + 1) * 10,
            ativo=True,
            estilos=copy.deepcopy(c_dict.get("estilos", {})),
            configuracao=copy.deepcopy(c_dict.get("configuracao", {})),
        )

        for idx_e, e_dict in enumerate(c_dict.get("elementos", [])):
            tipo = e_dict.get("tipo", "").lower()
            definicao = RegistroElementos.obter(tipo)
            conteudo_mesclado = definicao.conteudo_padrao()
            conteudo_mesclado.update(e_dict.get("conteudo", {}))

            estilos_mesclados = definicao.estilos_padrao()
            if e_dict.get("estilos"):
                estilos_mesclados.update(e_dict["estilos"])

            ElementoSite.objects.create(
                container=novo_c,
                tipo=tipo.upper(),
                ordem=(idx_e + 1) * 10,
                ativo=True,
                conteudo=conteudo_mesclado,
                estilos=estilos_mesclados,
                configuracao=copy.deepcopy(e_dict.get("configuracao", {})),
            )

        filhos = c_dict.get("filhos", [])
        if filhos:
            _instanciar_containers_recursivo(filhos, nova_secao, parent_container=novo_c)


def instanciar_template(
    template: TemplateSite,
    cliente: Cliente,
    nome: str,
    slug: str | None = None,
    tipo: str = ProjetoSite.Tipo.BIOSITE,
    descricao_interna: str = "",
) -> ProjetoSite:
    """
    Instancia atomicamente um novo ProjetoSite totalmente independente a partir de um TemplateSite.

    Garante:
    - Validação prévia de integridade e segurança do snapshot.
    - Criação de novos IDs, UUIDs e status RASCUNHO.
    - Cópia e vinculação de ConfiguracaoVisualProjeto com os tokens do modelo.
    - Rollback completo em caso de falha em qualquer nó da árvore.
    """
    validar_snapshot_template(template.estrutura_snapshot)

    slug_final = gerar_slug_unico(nome=nome, slug_sugerido=slug)

    with transaction.atomic():
        novo_projeto = ProjetoSite.objects.create(
            cliente=cliente,
            nome=nome,
            slug=slug_final,
            tipo=tipo,
            status=ProjetoSite.Status.RASCUNHO,
            descricao_interna=descricao_interna,
            template_origem=template,
        )

        # Configuração visual do template
        config_snapshot = template.estrutura_snapshot.get("configuracao_visual", {})
        config_visual = garantir_configuracao_visual(novo_projeto)
        for campo, val in config_snapshot.items():
            if hasattr(config_visual, campo) and val:
                setattr(config_visual, campo, val)
        config_visual.save()

        # Criação das páginas e seções
        paginas_snapshot = template.estrutura_snapshot.get("paginas", [])
        for idx_p, p_dict in enumerate(paginas_snapshot):
            slug_pag = p_dict.get("slug", "inicio")
            eh_inicial = p_dict.get("eh_inicial", idx_p == 0)

            nova_pag = PaginaSite.objects.create(
                projeto=novo_projeto,
                titulo=p_dict.get("titulo", "Início"),
                slug=slug_pag,
                ordem=(idx_p + 1) * 10,
                eh_inicial=eh_inicial,
                ativa=True,
            )

            secoes_snapshot = p_dict.get("secoes", [])
            for idx_s, s_dict in enumerate(secoes_snapshot):
                nova_s = SecaoSite.objects.create(
                    pagina=nova_pag,
                    nome_interno=s_dict.get("nome_interno", f"Seção {idx_s + 1}"),
                    tipo=s_dict.get("tipo", "normal"),
                    ordem=(idx_s + 1) * 10,
                    ativa=True,
                    estilos=copy.deepcopy(s_dict.get("estilos", {})),
                    configuracao=copy.deepcopy(s_dict.get("configuracao", {})),
                )
                _instanciar_containers_recursivo(s_dict.get("containers", []), nova_s)

        logger.info(
            "Template '%s' instanciado com sucesso no projeto '%s' (UUID: %s)",
            template.nome,
            novo_projeto.nome,
            novo_projeto.uuid,
        )
        return novo_projeto


def instanciar_bloco(
    bloco: BlocoReutilizavel, pagina: PaginaSite, ordem: int | None = None
) -> SecaoSite:
    """
    Insere atomicamente um BlocoReutilizavel em uma página existente como uma nova Seção independente.

    Garante validação do snapshot e preservação da hierarquia de containers e elementos.
    """
    validar_snapshot_bloco(bloco.estrutura_snapshot)

    secao_snapshot = bloco.estrutura_snapshot["secao"]

    with transaction.atomic():
        if ordem is None:
            maior_ordem = pagina.secoes.aggregate(max_ordem=Max("ordem"))["max_ordem"] or 0
            ordem = maior_ordem + 10

        nova_s = SecaoSite.objects.create(
            pagina=pagina,
            nome_interno=secao_snapshot.get("nome_interno", bloco.nome),
            tipo=secao_snapshot.get("tipo", "normal"),
            ordem=ordem,
            ativa=True,
            estilos=copy.deepcopy(secao_snapshot.get("estilos", {})),
            configuracao=copy.deepcopy(secao_snapshot.get("configuracao", {})),
        )

        _instanciar_containers_recursivo(secao_snapshot.get("containers", []), nova_s)

        logger.info(
            "Bloco '%s' inserido na página '%s' (ID: %d) como seção #%d",
            bloco.nome,
            pagina.titulo,
            pagina.id,
            nova_s.id,
        )
        return nova_s


def criar_template_a_partir_projeto(
    projeto: ProjetoSite,
    nome: str,
    categoria: str = TemplateSite.Categoria.BIOSITE,
    descricao: str = "",
    substituir_placeholders: bool = True,
) -> TemplateSite:
    """
    Transforma um ProjetoSite existente em um TemplateSite reutilizável na categoria 'Meus Modelos'.
    """
    nome_limpo = nome.strip()
    if not nome_limpo:
        raise ValidationError(_("O nome do modelo é obrigatório."))

    slug_base = slugify(nome_limpo) or "modelo"
    slug_candidato = slug_base
    contador = 2
    while TemplateSite.objects.filter(slug=slug_candidato).exists():
        slug_candidato = f"{slug_base}-{contador}"
        contador += 1

    snapshot = serializar_projeto_para_snapshot(
        projeto, substituir_placeholders=substituir_placeholders
    )
    validar_snapshot_template(snapshot)

    return TemplateSite.objects.create(
        nome=nome_limpo,
        slug=slug_candidato,
        descricao=descricao.strip(),
        categoria=categoria,
        origem=TemplateSite.Origem.USUARIO,
        versao=1,
        ativo=True,
        ordem=50,
        estrutura_snapshot=snapshot,
    )


def criar_bloco_a_partir_secao(
    secao: SecaoSite,
    nome: str,
    categoria: str = BlocoReutilizavel.Categoria.HERO,
    descricao: str = "",
    substituir_placeholders: bool = True,
) -> BlocoReutilizavel:
    """
    Transforma uma SecaoSite existente em um BlocoReutilizavel na categoria 'Meus Blocos'.
    """
    nome_limpo = nome.strip()
    if not nome_limpo:
        raise ValidationError(_("O nome do bloco é obrigatório."))

    slug_base = slugify(nome_limpo) or "bloco"
    slug_candidato = slug_base
    contador = 2
    while BlocoReutilizavel.objects.filter(slug=slug_candidato).exists():
        slug_candidato = f"{slug_base}-{contador}"
        contador += 1

    snapshot = serializar_secao_para_snapshot(
        secao, substituir_placeholders=substituir_placeholders
    )
    validar_snapshot_bloco(snapshot)

    return BlocoReutilizavel.objects.create(
        nome=nome_limpo,
        slug=slug_candidato,
        descricao=descricao.strip(),
        categoria=categoria,
        origem=BlocoReutilizavel.Origem.USUARIO,
        versao=1,
        ativo=True,
        ordem=50,
        estrutura_snapshot=snapshot,
    )
