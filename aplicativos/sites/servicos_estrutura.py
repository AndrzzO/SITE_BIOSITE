"""Serviços de manipulação, integridade, ordenação e duplicação profunda da árvore estrutural."""

import copy
import logging
from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Max, Prefetch
from django.utils.translation import gettext_lazy as _

from .models import ContainerSite, ElementoSite, PaginaSite, ProjetoSite, SecaoSite
from .servicos import gerar_slug_unico

logger = logging.getLogger("aplicativos.sites.servicos_estrutura")


def garantir_pagina_inicial(projeto: ProjetoSite) -> PaginaSite:
    """
    Garante de forma idempotente que o projeto possua uma página inicial definida.

    Se não existir, cria a página 'Início' com slug 'inicio' e eh_inicial=True.
    """
    pagina_home = PaginaSite.objects.filter(projeto=projeto, eh_inicial=True).first()
    if pagina_home:
        return pagina_home

    # Criação da home inicial padrão
    pagina_home = PaginaSite.objects.create(
        projeto=projeto,
        titulo="Início",
        slug="inicio",
        ordem=10,
        eh_inicial=True,
        ativa=True,
    )

    criar_secao_com_container_padrao(pagina_home, nome_interno="Seção Principal")

    logger.info(
        "Página inicial 'Início' com seção padrão criada para o projeto '%s' (UUID: %s)",
        projeto.nome,
        projeto.uuid,
    )
    return pagina_home


def criar_secao_com_container_padrao(
    pagina: PaginaSite,
    nome_interno: str,
    tipo: str = SecaoSite.Tipo.NORMAL,
) -> tuple[SecaoSite, ContainerSite]:
    """
    Cria uma nova seção acompanhada automaticamente de um container raiz do tipo STACK.

    Facilita a composição no editor e assegura que nenhuma seção nasça vazia de container.
    """
    with transaction.atomic():
        maior_ordem = pagina.secoes.aggregate(max_ordem=Max("ordem"))["max_ordem"] or 0
        nova_ordem = maior_ordem + 10

        secao = SecaoSite.objects.create(
            pagina=pagina,
            nome_interno=nome_interno,
            tipo=tipo,
            ordem=nova_ordem,
            ativa=True,
        )

        container = ContainerSite.objects.create(
            secao=secao,
            parent=None,
            tipo_layout=ContainerSite.TipoLayout.STACK,
            ordem=10,
            ativo=True,
        )

        return secao, container


def reordenar_entidades(
    classe_modelo: Any,
    lista_ids: list[int | str],
    filtro_pai_campo: str,
    filtro_pai_valor: Any,
) -> None:
    """
    Reordena de forma atômica uma lista de entidades irmãs utilizando passos de 10.

    Valida que todos os IDs informados pertencem ao mesmo pai antes de persistir.
    """
    with transaction.atomic():
        filtro = {filtro_pai_campo: filtro_pai_valor, "id__in": lista_ids}
        registros = {r.id: r for r in classe_modelo.objects.filter(**filtro)}

        if len(registros) != len(lista_ids):
            raise ValidationError(
                _("A lista de reordenação contém IDs inválidos ou de escopos divergentes.")
            )

        for indice, item_id in enumerate(lista_ids):
            registro = registros[int(item_id)]
            nova_ordem = (indice + 1) * 10
            if registro.ordem != nova_ordem:
                registro.ordem = nova_ordem
                registro.save(update_fields=["ordem", "atualizado_em"])


def duplicar_elemento(
    elemento: ElementoSite, novo_container: ContainerSite | None = None
) -> ElementoSite:
    """Clona profundamente um elemento para dentro de um container."""
    if novo_container is None:
        novo_container = elemento.container
        nova_ordem = elemento.ordem + 10
    else:
        nova_ordem = elemento.ordem

    return ElementoSite.objects.create(
        container=novo_container,
        tipo=elemento.tipo,
        ordem=nova_ordem,
        ativo=elemento.ativo,
        conteudo=copy.deepcopy(elemento.conteudo),
        estilos=copy.deepcopy(elemento.estilos),
        configuracao=copy.deepcopy(elemento.configuracao),
        versao_schema=elemento.versao_schema,
    )


def duplicar_container(
    container: ContainerSite,
    nova_secao: SecaoSite,
    novo_parent: ContainerSite | None = None,
) -> ContainerSite:
    """Clona recursivamente um container, seus elementos e eventuais containers filhos."""
    novo_c = ContainerSite.objects.create(
        secao=nova_secao,
        parent=novo_parent,
        ordem=container.ordem,
        tipo_layout=container.tipo_layout,
        ativo=container.ativo,
        configuracao=copy.deepcopy(container.configuracao),
        estilos=copy.deepcopy(container.estilos),
    )

    # Clona elementos deste container
    for elem in container.elementos.all().order_by("ordem"):
        duplicar_elemento(elem, novo_c)

    # Clona containers filhos recursivamente
    for filho in container.filhos.all().order_by("ordem"):
        duplicar_container(filho, nova_secao, novo_parent=novo_c)

    return novo_c


def duplicar_secao(secao: SecaoSite, nova_pagina: PaginaSite | None = None) -> SecaoSite:
    """Clona profundamente uma seção e toda a sua árvore de containers e elementos."""
    if nova_pagina is None:
        nova_pagina = secao.pagina

    with transaction.atomic():
        maior_ordem = nova_pagina.secoes.aggregate(max_ordem=Max("ordem"))["max_ordem"] or 0

        nova_s = SecaoSite.objects.create(
            pagina=nova_pagina,
            nome_interno=f"{secao.nome_interno} (Cópia)",
            ordem=maior_ordem + 10,
            tipo=secao.tipo,
            ativa=secao.ativa,
            configuracao=copy.deepcopy(secao.configuracao),
            estilos=copy.deepcopy(secao.estilos),
        )

        # Clona apenas os containers raiz da seção (aqueles com parent=None)
        for c_raiz in secao.containers.filter(parent__isnull=True).order_by("ordem"):
            duplicar_container(c_raiz, nova_s, novo_parent=None)

        return nova_s


def duplicar_pagina(pagina: PaginaSite, novo_projeto: ProjetoSite | None = None) -> PaginaSite:
    """Clona profundamente uma página e todas as suas seções para dentro de um projeto."""
    if novo_projeto is None:
        novo_projeto = pagina.projeto

    with transaction.atomic():
        slug_candidato = pagina.slug
        if pagina.projeto_id == novo_projeto.id:
            slug_candidato = f"{pagina.slug}-copia"
            contador = 2
            while PaginaSite.objects.filter(projeto=novo_projeto, slug=slug_candidato).exists():
                slug_candidato = f"{pagina.slug}-copia-{contador}"
                contador += 1

        eh_inicial = (
            pagina.eh_inicial
            and not PaginaSite.objects.filter(projeto=novo_projeto, eh_inicial=True).exists()
        )

        maior_ordem = novo_projeto.paginas.aggregate(max_ordem=Max("ordem"))["max_ordem"] or 0

        nova_pag = PaginaSite.objects.create(
            projeto=novo_projeto,
            titulo=f"{pagina.titulo} (Cópia)"
            if pagina.projeto_id == novo_projeto.id
            else pagina.titulo,
            slug=slug_candidato,
            ordem=maior_ordem + 10,
            eh_inicial=eh_inicial,
            ativa=pagina.ativa,
        )

        for secao in pagina.secoes.all().order_by("ordem"):
            duplicar_secao(secao, nova_pag)

        return nova_pag


def duplicar_projeto_completo(projeto_original: ProjetoSite) -> ProjetoSite:
    """
    Clona profundamente um ProjetoSite e TODA a sua árvore de páginas, seções, containers e elementos.

    Garante:
    - Execução atômica.
    - Novos IDs, novos UUIDs e novos timestamps.
    - Status forçado para RASCUNHO.
    - Slug único derivado.
    """
    with transaction.atomic():
        slug_base = f"{projeto_original.slug}-copia"
        novo_slug = gerar_slug_unico(
            nome=f"{projeto_original.nome} Copia",
            slug_sugerido=slug_base,
        )

        novo_projeto = ProjetoSite.objects.create(
            cliente=projeto_original.cliente,
            nome=f"Cópia de {projeto_original.nome}",
            slug=novo_slug,
            tipo=projeto_original.tipo,
            status=ProjetoSite.Status.RASCUNHO,
            descricao_interna=projeto_original.descricao_interna,
            thumbnail=projeto_original.thumbnail if projeto_original.thumbnail else None,
        )

        # Clona todas as páginas do projeto original
        for pag in projeto_original.paginas.all().order_by("ordem"):
            duplicar_pagina(pag, novo_projeto)

        # Garante que se o original não tinha página inicial por qualquer razão, a cópia tenha
        garantir_pagina_inicial(novo_projeto)

        logger.info(
            "Duplicação profunda do projeto '%s' (UUID: %s) concluída para '%s' (UUID: %s)",
            projeto_original.nome,
            projeto_original.uuid,
            novo_projeto.nome,
            novo_projeto.uuid,
        )

        return novo_projeto


def obter_estrutura_projeto(projeto: ProjetoSite, apenas_ativos: bool = False) -> dict[str, Any]:
    """
    Serializa a árvore estrutural completa do projeto em um dicionário otimizado.

    Utiliza prefetch_related aninhado e ordenado para eliminar completamente consultas N+1.
    """
    filtro_ativo = {"ativa": True} if apenas_ativos else {}
    filtro_elem_ativo = {"ativo": True} if apenas_ativos else {}

    elementos_prefetch = Prefetch(
        "elementos",
        queryset=ElementoSite.objects.filter(**filtro_elem_ativo).order_by("ordem"),
    )

    # Nível 3 (Netos)
    containers_netos_qs = (
        ContainerSite.objects.all().order_by("ordem").prefetch_related(elementos_prefetch)
    )

    # Nível 2 (Filhos)
    containers_filhos_qs = (
        ContainerSite.objects.all()
        .order_by("ordem")
        .prefetch_related(
            elementos_prefetch,
            Prefetch("filhos", queryset=containers_netos_qs),
        )
    )

    # Nível 1 (Raízes da Seção)
    containers_raiz_qs = (
        ContainerSite.objects.filter(parent__isnull=True)
        .order_by("ordem")
        .prefetch_related(
            elementos_prefetch,
            Prefetch("filhos", queryset=containers_filhos_qs),
        )
    )

    secoes_qs = (
        SecaoSite.objects.filter(**filtro_ativo)
        .order_by("ordem")
        .prefetch_related(
            Prefetch("containers", queryset=containers_raiz_qs, to_attr="containers_raiz"),
        )
    )

    paginas_qs = (
        projeto.paginas.filter(**filtro_ativo)
        .order_by("ordem")
        .prefetch_related(
            Prefetch("secoes", queryset=secoes_qs),
        )
    )

    def _serializar_container(c: ContainerSite) -> dict[str, Any]:
        return {
            "id": c.id,
            "uuid": str(c.uuid),
            "tipo_layout": c.tipo_layout,
            "ordem": c.ordem,
            "ativo": c.ativo,
            "configuracao": c.configuracao,
            "estilos": c.estilos,
            "elementos": [
                {
                    "id": elem.id,
                    "uuid": str(elem.uuid),
                    "tipo": elem.tipo,
                    "ordem": elem.ordem,
                    "ativo": elem.ativo,
                    "conteudo": elem.conteudo,
                    "estilos": elem.estilos,
                }
                for elem in c.elementos.all()
            ],
            "filhos": [_serializar_container(f) for f in c.filhos.all()],
        }

    dados = {
        "projeto": {
            "id": projeto.id,
            "uuid": str(projeto.uuid),
            "nome": projeto.nome,
            "slug": projeto.slug,
            "tipo": projeto.tipo,
            "status": projeto.status,
        },
        "paginas": [],
    }

    for pag in paginas_qs:
        secoes_dados = []
        for sec in pag.secoes.all():
            containers_dados = [_serializar_container(c) for c in sec.containers_raiz]
            secoes_dados.append(
                {
                    "id": sec.id,
                    "uuid": str(sec.uuid),
                    "nome_interno": sec.nome_interno,
                    "tipo": sec.tipo,
                    "ordem": sec.ordem,
                    "ativa": sec.ativa,
                    "configuracao": sec.configuracao,
                    "estilos": sec.estilos,
                    "containers": containers_dados,
                }
            )

        dados["paginas"].append(
            {
                "id": pag.id,
                "uuid": str(pag.uuid),
                "titulo": pag.titulo,
                "slug": pag.slug,
                "ordem": pag.ordem,
                "eh_inicial": pag.eh_inicial,
                "ativa": pag.ativa,
                "secoes": secoes_dados,
            }
        )

    return dados


def auditar_integridade_projeto(projeto: ProjetoSite) -> list[str]:
    """
    Audita a integridade referencial da árvore do projeto.

    Retorna lista de inconsistências encontradas (vazia se a árvore estiver saudável).
    """
    anomalias: list[str] = []

    # 1. Checagem de Home
    total_homes = projeto.paginas.filter(eh_inicial=True).count()
    if total_homes == 0:
        anomalias.append("O projeto não possui página inicial definida.")
    elif total_homes > 1:
        anomalias.append(
            f"O projeto possui {total_homes} páginas marcadas como inicial simultaneamente."
        )

    # 2. Checagem de slugs de páginas duplicados
    slugs = list(projeto.paginas.values_list("slug", flat=True))
    if len(slugs) != len(set(slugs)):
        anomalias.append("Existem páginas com slugs duplicados no mesmo projeto.")

    # 3. Checagem de containers órfãos ou que cruzaram seções
    for container in ContainerSite.objects.filter(secao__pagina__projeto=projeto):
        if container.parent and container.parent.secao_id != container.secao_id:
            anomalias.append(
                f"Container #{container.id} possui container pai pertencente a seção diferente."
            )
        try:
            container.obter_profundidade()
        except ValidationError as e:
            anomalias.append(f"Erro no container #{container.id}: {e.message}")

    return anomalias
