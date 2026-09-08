"""
Serviços de domínio para o ciclo de vida de Rascunho, Validação Pré-Publicação,
Versionamento Imutável, Publicação, Rollback e Caching de BioSites (Prompt 8).
"""

import copy
import hashlib
import json
import logging
from typing import Any

from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .elementos.registry import RegistroElementos
from .models import (
    ContainerSite,
    MidiaSite,
    PaginaSite,
    ProjetoSite,
    PublicacaoSite,
    SecaoSite,
    garantir_configuracao_visual,
)

logger = logging.getLogger("aplicativos.sites.servicos_publicacao")

SCHEMA_VERSION_PUBLICACAO: int = 1
CACHE_PREFIX_SITE_PUBLICO: str = "biosite_pub"
CACHE_TTL_SITE_PUBLICO: int = 3600  # 1 hora


# =============================================================================
# HASH CANÔNICO E NORMALIZAÇÃO DE SNAPSHOT
# =============================================================================


def extrair_conteudo_canonico(snapshot: dict[str, Any]) -> dict[str, Any]:
    """
    Extrai do snapshot exclusivamente os nós funcionais e visuais de conteúdo,
    removendo metadados de execução (datas, IDs transitórios, timestamps)
    para cálculo de hash puramente determinístico.
    """
    return {
        "schema_version": snapshot.get("schema_version", 1),
        "configuracao_visual": snapshot.get("configuracao_visual", {}),
        "paginas": snapshot.get("paginas", []),
        "seo": snapshot.get("projeto", {}),
    }


def calcular_hash_conteudo(snapshot: dict[str, Any]) -> str:
    """Calcula o hash SHA-256 canônico e determinístico do conteúdo publicado."""
    conteudo_puro = extrair_conteudo_canonico(snapshot)
    payload_json = json.dumps(
        conteudo_puro,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(payload_json.encode("utf-8")).hexdigest()


# =============================================================================
# VALIDAÇÃO PRÉ-PUBLICAÇÃO
# =============================================================================


def validar_pre_publicacao(projeto: ProjetoSite) -> tuple[bool, list[str], list[str]]:
    """
    Executa auditoria abrangente do rascunho antes da publicação.

    Retorna:
    - valido (bool): True se não existirem erros impeditivos/bloqueantes.
    - erros_bloqueantes (list[str]): Falhas críticas que impedem a publicação.
    - avisos_nao_bloqueantes (list[str]): Alertas informativos de SEO e boas práticas.
    """
    erros: list[str] = []
    avisos: list[str] = []

    # 1. Validação de Páginas
    paginas = projeto.paginas.filter(ativa=True).order_by("ordem")
    if not paginas.exists():
        erros.append("O site não possui nenhuma página ativa criada.")
        return False, erros, avisos

    pagina_inicial = paginas.filter(eh_inicial=True).first()
    if not pagina_inicial:
        erros.append("O site não possui uma página inicial (Home) definida.")
    else:
        secoes_home = pagina_inicial.secoes.filter(ativa=True)
        if not secoes_home.exists():
            erros.append("A página inicial do site não possui nenhuma seção criada.")

    # 2. Validação de Nós, Componentes e URLs Perigosas
    for pag in paginas:
        for secao in pag.secoes.filter(ativa=True):
            for container in secao.containers.filter(ativo=True):
                for elem in container.elementos.filter(ativo=True):
                    # Valida tipo registrado
                    tipo = elem.tipo.lower()
                    if not RegistroElementos.eh_valido(tipo):
                        erros.append(
                            f"Elemento com tipo desconhecido '{elem.tipo}' encontrado na seção '{secao.nome_interno}'."
                        )
                        continue

                    # Valida URLs inseguras no conteúdo
                    conteudo = elem.conteudo or {}
                    for chave in ("url", "link", "endereco", "url_externa"):
                        val_url = str(conteudo.get(chave, "")).strip().lower()
                        if val_url.startswith(("javascript:", "data:text/html", "vbscript:")):
                            erros.append(
                                f"URL perigosa ou insegura detectada no elemento '{elem.tipo}': '{val_url}'."
                            )

                    # Avisos de SEO e boas práticas (Não bloqueantes)
                    if tipo in ("imagem", "avatar"):
                        if not conteudo.get("alt"):
                            avisos.append(
                                f"Imagem na seção '{secao.nome_interno}' não possui texto alternativo (alt)."
                            )
                    elif tipo == "whatsapp":
                        numero = str(conteudo.get("numero", "")).strip()
                        if not numero or numero == "00000000000":
                            avisos.append(
                                "Botão de WhatsApp encontrado sem número de telefone devidamente configurado."
                            )

    # 3. Avisos de Metadados de SEO
    if not projeto.descricao_seo:
        avisos.append(
            "A descrição SEO (meta description) não foi informada. Buscadores e redes sociais exibirão descrição padrão."
        )
    if not projeto.imagem_compartilhamento:
        avisos.append(
            "Nenhuma imagem de compartilhamento social (OG Image) foi selecionada para o site."
        )

    valido = len(erros) == 0
    return valido, erros, avisos


# =============================================================================
# SERIALIZAÇÃO DE PUBLICAÇÃO
# =============================================================================


def _serializar_container_publicacao(
    container: ContainerSite, midias_acumuladas: set[int]
) -> dict[str, Any]:
    elementos = []
    for elem in container.elementos.filter(ativo=True).order_by("ordem"):
        elem_conteudo = copy.deepcopy(elem.conteudo)
        # Rastreia mídias referenciadas
        for chave_m in ("midia_id", "imagem_id", "arquivo_id"):
            val_m = elem_conteudo.get(chave_m)
            if val_m:
                if isinstance(val_m, int):
                    midias_acumuladas.add(val_m)
                elif isinstance(val_m, str) and val_m.isdigit():
                    midias_acumuladas.add(int(val_m))
                else:
                    m_id = MidiaSite.objects.filter(uuid=val_m).values_list("id", flat=True).first()
                    if m_id:
                        midias_acumuladas.add(m_id)

        elementos.append(
            {
                "tipo": elem.tipo.lower(),
                "conteudo": elem_conteudo,
                "estilos": copy.deepcopy(elem.estilos),
                "configuracao": copy.deepcopy(elem.configuracao),
            }
        )

    filhos = [
        _serializar_container_publicacao(f, midias_acumuladas)
        for f in container.filhos.filter(ativo=True).order_by("ordem")
    ]

    return {
        "tipo_layout": container.tipo_layout,
        "estilos": copy.deepcopy(container.estilos),
        "configuracao": copy.deepcopy(container.configuracao),
        "elementos": elementos,
        "filhos": filhos,
    }


def serializar_projeto_para_publicacao(
    projeto: ProjetoSite,
) -> tuple[dict[str, Any], list[MidiaSite]]:
    """
    Serializa o estado atual do rascunho de um projeto em um snapshot pronto para publicação.

    Retorna:
    - snapshot (dict): Representação estrutural canônica de produção.
    - midias_usadas (list[MidiaSite]): Lista de instâncias de mídias que devem ser retidas.
    """
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

    midias_ids: set[int] = set()
    if projeto.imagem_compartilhamento_id:
        midias_ids.add(projeto.imagem_compartilhamento_id)

    paginas_serializadas = []
    for pag in projeto.paginas.filter(ativa=True).order_by("ordem"):
        secoes_serializadas = []
        for s in pag.secoes.filter(ativa=True).order_by("ordem"):
            containers_raiz = s.containers.filter(parent__isnull=True, ativo=True).order_by("ordem")
            containers_serializados = [
                _serializar_container_publicacao(c, midias_ids) for c in containers_raiz
            ]
            secoes_serializadas.append(
                {
                    "nome_interno": s.nome_interno,
                    "tipo": s.tipo,
                    "estilos": copy.deepcopy(s.estilos),
                    "configuracao": copy.deepcopy(s.configuracao),
                    "containers": containers_serializados,
                }
            )

        paginas_serializadas.append(
            {
                "titulo": pag.titulo,
                "slug": pag.slug,
                "eh_inicial": pag.eh_inicial,
                "secoes": secoes_serializadas,
            }
        )

    # Metadados públicos essenciais
    projeto_meta = {
        "nome": projeto.nome,
        "slug": projeto.slug,
        "tipo": projeto.tipo,
        "titulo_seo": projeto.titulo_seo or projeto.nome,
        "descricao_seo": projeto.descricao_seo or "",
        "imagem_og": (
            projeto.imagem_compartilhamento.arquivo.url
            if projeto.imagem_compartilhamento and projeto.imagem_compartilhamento.arquivo
            else ""
        ),
        "indexavel": projeto.indexavel,
    }

    snapshot = {
        "schema_version": SCHEMA_VERSION_PUBLICACAO,
        "projeto": projeto_meta,
        "configuracao_visual": config_dict,
        "paginas": paginas_serializadas,
    }

    midias_usadas = list(MidiaSite.objects.filter(id__in=midias_ids))
    return snapshot, midias_usadas


# =============================================================================
# SERVIÇO CENTRAL DE PUBLICAÇÃO
# =============================================================================


def publicar_projeto(
    projeto: ProjetoSite,
    usuario: Any = None,
    forcar: bool = False,
) -> PublicacaoSite:
    """
    Publica o rascunho atual gerando uma nova versão imutável (v1, v2, v3...).

    Garante:
    - Validação de integridade e bloqueio de erros impeditivos.
    - Execução atômica e bloqueio seletivo contra concorrência (select_for_update).
    - Hash determinístico do conteúdo publicado.
    - Detecção de publicação idêntica sem modificação.
    - Associação protetiva das mídias referenciadas.
    - Desativação limpa de versões anteriores.
    - Invalidação automática do cache público.
    """
    valido, erros, avisos = validar_pre_publicacao(projeto)
    if not valido:
        raise ValidationError(erros)

    snapshot, midias_usadas = serializar_projeto_para_publicacao(projeto)
    hash_novo = calcular_hash_conteudo(snapshot)

    # Verifica se já existe publicação ativa idêntica
    if not forcar and projeto.publicacao_ativa:
        if projeto.publicacao_ativa.hash_conteudo == hash_novo:
            raise ValidationError(
                _(
                    "Não há alterações pendentes no rascunho. O site já está publicado com este conteúdo."
                )
            )

    with transaction.atomic():
        # Bloqueia a linha do projeto contra concorrência durante a publicação
        projeto_lock = ProjetoSite.objects.select_for_update().get(id=projeto.id)

        # Determina o próximo número de versão estritamente sequencial
        max_versao = projeto_lock.publicacoes.aggregate(m=models.Max("numero_versao"))["m"] or 0
        proxima_versao = max_versao + 1

        nova_publicacao = PublicacaoSite.objects.create(
            projeto=projeto_lock,
            numero_versao=proxima_versao,
            snapshot=snapshot,
            schema_version=SCHEMA_VERSION_PUBLICACAO,
            hash_conteudo=hash_novo,
            publicado_em=timezone.now(),
            publicado_por=usuario if (usuario and usuario.is_authenticated) else None,
            ativa=True,
            metadata={
                "total_paginas": len(snapshot.get("paginas", [])),
                "origem_publicacao": "editor",
            },
        )

        if midias_usadas:
            nova_publicacao.midias_referenciadas.set(midias_usadas)

        # Desativa outras publicações do projeto
        projeto_lock.publicacoes.exclude(id=nova_publicacao.id).filter(ativa=True).update(
            ativa=False
        )

        # Atualiza o ponteiro de publicação ativa e o status
        projeto_lock.publicacao_ativa = nova_publicacao
        projeto_lock.status = ProjetoSite.Status.PUBLICADO
        projeto_lock.save(update_fields=["publicacao_ativa", "status", "atualizado_em"])

        # Sincroniza a instância passada
        projeto.publicacao_ativa = nova_publicacao
        projeto.status = ProjetoSite.Status.PUBLICADO

    # Invalidação de Cache
    invalidar_cache_site_publico(projeto)

    logger.info(
        "Projeto '%s' (UUID: %s) publicado com sucesso na versão v%s (Hash: %s).",
        projeto.nome,
        projeto.uuid,
        nova_publicacao.numero_versao,
        hash_novo[:8],
    )

    return nova_publicacao


# =============================================================================
# ROLLBACK CRONOLÓGICO
# =============================================================================


def rollback_publicacao(
    projeto: ProjetoSite,
    publicacao_alvo: PublicacaoSite,
    usuario: Any = None,
) -> PublicacaoSite:
    """
    Restaura uma versão anterior criando uma NOVA versão no histórico (Rollback Cronológico).

    Exemplo:
        v1 -> v2 -> v3 (atual)
        Restaurar v1 cria v4 com o mesmo snapshot e hash de v1.
    """
    if publicacao_alvo.projeto_id != projeto.id:
        raise ValidationError(_("A versão alvo não pertence a este projeto."))

    with transaction.atomic():
        projeto_lock = ProjetoSite.objects.select_for_update().get(id=projeto.id)

        max_versao = projeto_lock.publicacoes.aggregate(m=models.Max("numero_versao"))["m"] or 0
        proxima_versao = max_versao + 1

        nova_publicacao = PublicacaoSite.objects.create(
            projeto=projeto_lock,
            numero_versao=proxima_versao,
            snapshot=copy.deepcopy(publicacao_alvo.snapshot),
            schema_version=publicacao_alvo.schema_version,
            hash_conteudo=publicacao_alvo.hash_conteudo,
            publicado_em=timezone.now(),
            publicado_por=usuario if (usuario and usuario.is_authenticated) else None,
            ativa=True,
            metadata={
                "origem": "rollback",
                "versao_restaurada": publicacao_alvo.numero_versao,
                "data_restauracao": timezone.now().isoformat(),
            },
        )

        # Copia referências de mídia
        nova_publicacao.midias_referenciadas.set(publicacao_alvo.midias_referenciadas.all())

        # Desativa outras versões
        projeto_lock.publicacoes.exclude(id=nova_publicacao.id).filter(ativa=True).update(
            ativa=False
        )

        # Atualiza ponteiro no projeto
        projeto_lock.publicacao_ativa = nova_publicacao
        projeto_lock.status = ProjetoSite.Status.PUBLICADO
        projeto_lock.save(update_fields=["publicacao_ativa", "status", "atualizado_em"])

        projeto.publicacao_ativa = nova_publicacao
        projeto.status = ProjetoSite.Status.PUBLICADO

    invalidar_cache_site_publico(projeto)

    logger.info(
        "Rollback executado no projeto '%s'. Versão v%s restaurada como nova versão v%s.",
        projeto.nome,
        publicacao_alvo.numero_versao,
        nova_publicacao.numero_versao,
    )

    return nova_publicacao


# =============================================================================
# DESPUBLICAÇÃO
# =============================================================================


def despublicar_projeto(projeto: ProjetoSite, usuario: Any = None) -> None:
    """
    Remove o site do ar desativando a publicação ativa, preservando todo o histórico.

    O status do projeto volta para RASCUNHO e a URL pública retorna 404.
    """
    with transaction.atomic():
        projeto_lock = ProjetoSite.objects.select_for_update().get(id=projeto.id)

        projeto_lock.publicacoes.filter(ativa=True).update(ativa=False)
        projeto_lock.publicacao_ativa = None
        projeto_lock.status = ProjetoSite.Status.RASCUNHO
        projeto_lock.save(update_fields=["publicacao_ativa", "status", "atualizado_em"])

        projeto.publicacao_ativa = None
        projeto.status = ProjetoSite.Status.RASCUNHO

    invalidar_cache_site_publico(projeto)

    logger.info(
        "Projeto '%s' (UUID: %s) despublicado com sucesso por %s.",
        projeto.nome,
        projeto.uuid,
        usuario,
    )


# =============================================================================
# RESTAURAR VERSÃO NO EDITOR (RASCUNHO)
# =============================================================================


def restaurar_versao_no_editor(projeto: ProjetoSite, publicacao: PublicacaoSite) -> None:
    """
    Substitui a árvore relacional de rascunho do projeto com a estrutura de uma publicação.

    Ação forte que sobrescreve páginas, seções, containers e elementos do rascunho
    para sincronizá-lo fielmente com a versão histórica selecionada.
    """
    from .servicos_templates import _instanciar_containers_recursivo

    if publicacao.projeto_id != projeto.id:
        raise ValidationError(_("A versão não pertence a este projeto."))

    snapshot = publicacao.snapshot

    with transaction.atomic():
        projeto_lock = ProjetoSite.objects.select_for_update().get(id=projeto.id)

        # 1. Atualiza configuração visual
        config_dict = snapshot.get("configuracao_visual", {})
        config_obj = garantir_configuracao_visual(projeto_lock)
        for campo, val in config_dict.items():
            if hasattr(config_obj, campo):
                setattr(config_obj, campo, val)
        config_obj.save()

        # 2. Atualiza metadados de SEO
        meta = snapshot.get("projeto", {})
        if meta.get("titulo_seo"):
            projeto_lock.titulo_seo = meta["titulo_seo"]
        if meta.get("descricao_seo"):
            projeto_lock.descricao_seo = meta["descricao_seo"]
        if "indexavel" in meta:
            projeto_lock.indexavel = meta["indexavel"]
        projeto_lock.save(update_fields=["titulo_seo", "descricao_seo", "indexavel"])

        # 3. Substitui páginas e estrutura relacional
        projeto_lock.paginas.all().delete()

        for idx_p, pag_dict in enumerate(snapshot.get("paginas", [])):
            nova_pag = PaginaSite.objects.create(
                projeto=projeto_lock,
                titulo=pag_dict.get("titulo", f"Página {idx_p + 1}"),
                slug=pag_dict.get("slug", f"pagina-{idx_p + 1}"),
                eh_inicial=pag_dict.get("eh_inicial", idx_p == 0),
                ordem=(idx_p + 1) * 10,
                ativa=True,
            )

            for idx_s, secao_dict in enumerate(pag_dict.get("secoes", [])):
                nova_secao = SecaoSite.objects.create(
                    pagina=nova_pag,
                    nome_interno=secao_dict.get("nome_interno", f"Seção {idx_s + 1}"),
                    tipo=secao_dict.get("tipo", "normal"),
                    ordem=(idx_s + 1) * 10,
                    ativa=True,
                    estilos=copy.deepcopy(secao_dict.get("estilos", {})),
                    configuracao=copy.deepcopy(secao_dict.get("configuracao", {})),
                )

                _instanciar_containers_recursivo(
                    secao_dict.get("containers", []), nova_secao=nova_secao
                )

        logger.info(
            "Rascunho do projeto '%s' substituído com sucesso pelo snapshot da versão v%s.",
            projeto.nome,
            publicacao.numero_versao,
        )


# =============================================================================
# DETECÇÃO DE ALTERAÇÕES PENDENTES
# =============================================================================


def verificar_alteracoes_pendentes(projeto: ProjetoSite) -> bool:
    """Compara o hash do rascunho atual com o hash da publicação ativa."""
    if not projeto.publicacao_ativa:
        return projeto.paginas.filter(ativa=True).exists()

    try:
        snapshot_rascunho, _ = serializar_projeto_para_publicacao(projeto)
        hash_rascunho = calcular_hash_conteudo(snapshot_rascunho)
        return hash_rascunho != projeto.publicacao_ativa.hash_conteudo
    except Exception as e:
        logger.warning("Erro ao comparar alterações pendentes para projeto %s: %s", projeto.uuid, e)
        return True


# =============================================================================
# CACHING DE ALTA PERFORMANCE PARA O SITE PÚBLICO
# =============================================================================


def obter_cache_key_site_publico(projeto_uuid: str, versao: int, pagina_slug: str = "") -> str:
    """Gera chave de cache padronizada para resposta HTML pública."""
    return f"{CACHE_PREFIX_SITE_PUBLICO}:{projeto_uuid}:v{versao}:{pagina_slug or 'home'}"


def invalidar_cache_site_publico(projeto: ProjetoSite) -> None:
    """Invalida todas as chaves de cache público associadas ao projeto."""
    try:
        # Invalida resolução de slug
        cache.delete(f"{CACHE_PREFIX_SITE_PUBLICO}:slug:{projeto.slug}")

        # Se houver versão ativa ou histórico recente, deleta chaves de páginas comuns
        for pub in projeto.publicacoes.all():
            cache.delete(obter_cache_key_site_publico(str(projeto.uuid), pub.numero_versao, ""))
            cache.delete(obter_cache_key_site_publico(str(projeto.uuid), pub.numero_versao, "home"))
            cache.delete(
                obter_cache_key_site_publico(str(projeto.uuid), pub.numero_versao, "inicio")
            )
            for pag in projeto.paginas.all():
                cache.delete(
                    obter_cache_key_site_publico(str(projeto.uuid), pub.numero_versao, pag.slug)
                )
    except Exception as e:
        logger.warning("Falha ao invalidar cache do site público %s: %s", projeto.uuid, e)
