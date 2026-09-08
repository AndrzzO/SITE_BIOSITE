"""
Serviços de Analytics first-party, privacy-friendly e mobile-first (Prompt 11).

REGRAS ARQUITETURAIS:
1. First-Party & Cookieless: Nenhum dado de terceiro, cookie de rastreamento ou identificação
   pessoal do visitante é criado ou manipulado.
2. Assinatura Criptográfica: Tokens de página e clique assinados via django.core.signing
   impedem falsificação de contexto ou injeção de IDs arbitrários.
3. Fail-Open Absoluto: Nenhuma falha de escrita no analytics pode interromper a renderização
   do BioSite, a navegação do visitante ou os redirecionamentos NFC/QR.
4. Anonimização Total: IP bruto e User-Agent integral NUNCA são persistidos no banco de dados.
5. Filtro de Bots Leve: Ignora crawlers e robôs conhecidos antes da persistência.
"""

import hashlib
import logging
import re
from datetime import datetime, time, timedelta
from typing import Any

from django.conf import settings
from django.core import signing
from django.core.cache import cache
from django.db.models import Count, Q
from django.http import HttpRequest
from django.utils import timezone

from .models import EventoAnalitico, LinkInteligente, ProjetoSite, PublicacaoSite

logger = logging.getLogger("aplicativos.sites.servicos_analytics")

SALT_ANALYTICS_PAGEVIEW = "biosite.analytics.pageview"
SALT_ANALYTICS_CLICK = "biosite.analytics.click"

# Regex leve para detecção de bots e crawlers conhecidos
REGEX_BOTS = re.compile(
    r"(googlebot|bingbot|yandex|duckduckbot|slurp|baiduspider|facebookexternalhit|"
    r"whatsapp|telegrambot|twitterbot|crawler|spider|robot|headless|phantomjs|"
    r"ahrefs|semrush|mj12bot|bytespider|petalbot|curl|wget|python-requests)",
    re.IGNORECASE,
)


def detectar_bot(user_agent: str | None) -> bool:
    """Verifica se o cabeçalho User-Agent corresponde a um crawler/bot comum."""
    if not user_agent:
        return False
    return bool(REGEX_BOTS.search(user_agent))


def verificar_rate_limit(
    request: HttpRequest | None,
    chave_prefixo: str = "evt",
    limite: int = 120,
    janela_segundos: int = 60,
) -> bool:
    """
    Rate limiting transitório baseado em hash efêmero do IP.
    O IP NUNCA é salvo no banco de dados, apenas no cache temporário com TTL curto.
    """
    if not request:
        return True

    ip = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if ip:
        ip = ip.split(",")[0].strip()
    else:
        ip = request.META.get("REMOTE_ADDR", "")

    if not ip:
        return True

    secret = getattr(settings, "SECRET_KEY", "analytics-salt")
    ip_hash = hashlib.sha256(f"{secret}:{ip}".encode()).hexdigest()[:16]
    cache_key = f"rl:{chave_prefixo}:{ip_hash}"

    try:
        contagem = cache.get(cache_key)
        if contagem is None:
            cache.set(cache_key, 1, timeout=janela_segundos)
            return True
        if contagem >= limite:
            logger.warning("Rate limit excedido para hash temporário '%s'.", ip_hash)
            return False
        cache.incr(cache_key)
        return True
    except Exception as err:
        logger.warning("Falha ao consultar cache de rate limit: %s", err)
        return True


# =============================================================================
# ASSINATURA E VALIDAÇÃO CRIPTOGRÁFICA DE TOKENS
# =============================================================================


def gerar_token_pageview(
    projeto_id: int, publicacao_id: int | None, pagina_slug: str | None = None
) -> str:
    """Gera um token criptográfico assinado pelo servidor para registrar visualização de página."""
    payload = {
        "p": projeto_id,
        "v": publicacao_id,
        "pg": pagina_slug or "",
        "t": EventoAnalitico.TipoEvento.PAGE_VIEW,
    }
    return signing.dumps(payload, salt=SALT_ANALYTICS_PAGEVIEW)


def gerar_token_clique(
    projeto_id: int,
    publicacao_id: int | None,
    tipo_componente: str,
    elemento_id: Any,
    subitem_id: str | None = None,
) -> str:
    """Gera um token criptográfico assinado pelo servidor para registrar clique em componente."""
    payload = {
        "p": projeto_id,
        "v": publicacao_id,
        "c": str(tipo_componente).upper(),
        "e": str(elemento_id or ""),
        "s": str(subitem_id or ""),
        "t": EventoAnalitico.TipoEvento.COMPONENT_CLICK,
    }
    return signing.dumps(payload, salt=SALT_ANALYTICS_CLICK)


def validar_token_evento(token: str) -> dict[str, Any] | None:
    """Valida um token assinado e extrai os metadados protegidos contra adulteração."""
    if not token or not isinstance(token, str):
        return None

    # Tenta validar como token de PageView
    try:
        dados = signing.loads(token, salt=SALT_ANALYTICS_PAGEVIEW, max_age=86400 * 90)
        if isinstance(dados, dict) and dados.get("t") == EventoAnalitico.TipoEvento.PAGE_VIEW:
            return dados
    except (signing.BadSignature, signing.SignatureExpired):
        pass

    # Tenta validar como token de Clique
    try:
        dados = signing.loads(token, salt=SALT_ANALYTICS_CLICK, max_age=86400 * 90)
        if isinstance(dados, dict) and dados.get("t") == EventoAnalitico.TipoEvento.COMPONENT_CLICK:
            return dados
    except (signing.BadSignature, signing.SignatureExpired):
        pass

    return None


# =============================================================================
# INGESTÃO DE EVENTOS (FAIL-OPEN)
# =============================================================================


def registrar_evento(
    projeto: ProjetoSite,
    tipo_evento: str,
    origem: str = EventoAnalitico.OrigemAcesso.DIRETO_DESCONHECIDO,
    publicacao: PublicacaoSite | None = None,
    pagina_uuid: str | None = None,
    elemento_uuid: str | None = None,
    tipo_componente: str | None = None,
    subitem_id: str | None = None,
    link_inteligente: LinkInteligente | None = None,
    contexto_minimo: dict[str, Any] | None = None,
    request: HttpRequest | None = None,
) -> EventoAnalitico | None:
    """
    Registra um evento analítico de forma leve, privacy-friendly e fail-open.
    Nunca levanta exceções ou bloqueia o usuário em caso de falha no banco de dados.
    """
    try:
        if request:
            ua = request.META.get("HTTP_USER_AGENT", "")
            if detectar_bot(ua):
                logger.debug("Bot detectado pelo User-Agent; evento não registrado.")
                return None

            if not verificar_rate_limit(request):
                return None

        # Resolve publicação ativa se não informada
        if not publicacao and projeto:
            publicacao = getattr(projeto, "publicacao_ativa", None)

        evento = EventoAnalitico.objects.create(
            projeto=projeto,
            publicacao=publicacao,
            tipo_evento=tipo_evento,
            origem=origem,
            pagina_uuid=pagina_uuid,
            elemento_uuid=elemento_uuid,
            tipo_componente=tipo_componente,
            subitem_id=subitem_id,
            link_inteligente=link_inteligente,
            contexto_minimo=contexto_minimo or {},
        )
        return evento
    except Exception as err:
        logger.error(
            "Erro não-crítico ao registrar evento analítico para o projeto %s: %s",
            getattr(projeto, "slug", "desconhecido"),
            err,
        )
        return None


# =============================================================================
# INTERVALOS DE TEMPO E DATAS
# =============================================================================


def resolver_intervalo_datas(
    periodo: str = "30d",
    data_inicio: str | None = None,
    data_fim: str | None = None,
) -> tuple[datetime, datetime, str]:
    """Calcula o intervalo de datas respeitando o timezone local da aplicação."""
    tz = timezone.get_current_timezone()
    agora_local = timezone.localtime(timezone.now(), tz)
    hoje = agora_local.date()

    if periodo == "hoje":
        inicio_dt = datetime.combine(hoje, time.min, tzinfo=tz)
        fim_dt = datetime.combine(hoje, time.max, tzinfo=tz)
        rotulo = "Hoje"
    elif periodo == "7d":
        inicio_date = hoje - timedelta(days=6)
        inicio_dt = datetime.combine(inicio_date, time.min, tzinfo=tz)
        fim_dt = datetime.combine(hoje, time.max, tzinfo=tz)
        rotulo = "Últimos 7 dias"
    elif periodo == "custom" and data_inicio and data_fim:
        try:
            d_ini = datetime.strptime(data_inicio, "%Y-%m-%d").date()
            d_fim = datetime.strptime(data_fim, "%Y-%m-%d").date()
            if d_ini > d_fim:
                d_ini, d_fim = d_fim, d_ini
            # Limita período customizado a no máximo 180 dias
            if (d_fim - d_ini).days > 180:
                d_ini = d_fim - timedelta(days=180)
            inicio_dt = datetime.combine(d_ini, time.min, tzinfo=tz)
            fim_dt = datetime.combine(d_fim, time.max, tzinfo=tz)
            rotulo = f"{d_ini:%d/%m/%Y} a {d_fim:%d/%m/%Y}"
        except ValueError:
            inicio_date = hoje - timedelta(days=29)
            inicio_dt = datetime.combine(inicio_date, time.min, tzinfo=tz)
            fim_dt = datetime.combine(hoje, time.max, tzinfo=tz)
            rotulo = "Últimos 30 dias"
    else:  # Padrão: 30 dias
        inicio_date = hoje - timedelta(days=29)
        inicio_dt = datetime.combine(inicio_date, time.min, tzinfo=tz)
        fim_dt = datetime.combine(hoje, time.max, tzinfo=tz)
        rotulo = "Últimos 30 dias"

    return inicio_dt, fim_dt, rotulo


# =============================================================================
# CONSULTAS E MÉTRICAS DO PROJETO (CACHE CURTO DE 60s)
# =============================================================================


def obter_metricas_projeto(
    projeto: ProjetoSite,
    periodo: str = "30d",
    data_inicio: str | None = None,
    data_fim: str | None = None,
    versao: int | None = None,
) -> dict[str, Any]:
    """Retorna o resumo numérico das métricas de um projeto em um dado intervalo."""
    dt_inicio, dt_fim, rotulo = resolver_intervalo_datas(periodo, data_inicio, data_fim)

    cache_key = (
        f"ana_metr:{projeto.id}:{periodo}:{dt_inicio.date()}:{dt_fim.date()}:{versao or 'all'}"
    )
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    qs = EventoAnalitico.objects.filter(
        projeto=projeto,
        ocorrido_em__gte=dt_inicio,
        ocorrido_em__lte=dt_fim,
    )
    if versao:
        qs = qs.filter(publicacao__numero_versao=versao)

    agregado = qs.aggregate(
        visualizacoes=Count("id", filter=Q(tipo_evento=EventoAnalitico.TipoEvento.PAGE_VIEW)),
        acessos_nfc=Count("id", filter=Q(tipo_evento=EventoAnalitico.TipoEvento.SMARTLINK_NFC)),
        acessos_qr=Count("id", filter=Q(tipo_evento=EventoAnalitico.TipoEvento.SMARTLINK_QR)),
        cliques_totais=Count(
            "id", filter=Q(tipo_evento=EventoAnalitico.TipoEvento.COMPONENT_CLICK)
        ),
        cliques_whatsapp=Count(
            "id",
            filter=Q(
                tipo_evento=EventoAnalitico.TipoEvento.COMPONENT_CLICK,
                tipo_componente="WHATSAPP",
            ),
        ),
        cliques_agenda=Count(
            "id",
            filter=Q(
                tipo_evento=EventoAnalitico.TipoEvento.COMPONENT_CLICK,
                tipo_componente="AGENDAMENTO_EXTERNO",
            ),
        ),
        cliques_telefone=Count(
            "id",
            filter=Q(
                tipo_evento=EventoAnalitico.TipoEvento.COMPONENT_CLICK,
                tipo_componente="TELEFONE",
            ),
        ),
        cliques_email=Count(
            "id",
            filter=Q(
                tipo_evento=EventoAnalitico.TipoEvento.COMPONENT_CLICK,
                tipo_componente="EMAIL",
            ),
        ),
    )

    visualizacoes = agregado["visualizacoes"] or 0
    cliques_totais = agregado["cliques_totais"] or 0
    cliques_whatsapp = agregado["cliques_whatsapp"] or 0

    ctr_aproximado = round((cliques_totais / visualizacoes) * 100, 1) if visualizacoes > 0 else 0.0
    ctr_whatsapp = round((cliques_whatsapp / visualizacoes) * 100, 1) if visualizacoes > 0 else 0.0

    resultado = {
        "visualizacoes": visualizacoes,
        "acessos_nfc": agregado["acessos_nfc"] or 0,
        "acessos_qr": agregado["acessos_qr"] or 0,
        "cliques_totais": cliques_totais,
        "ctr_aproximado": ctr_aproximado,
        "cliques_whatsapp": cliques_whatsapp,
        "ctr_whatsapp": ctr_whatsapp,
        "cliques_agenda": agregado["cliques_agenda"] or 0,
        "cliques_telefone": agregado["cliques_telefone"] or 0,
        "cliques_email": agregado["cliques_email"] or 0,
        "periodo": periodo,
        "periodo_rotulo": rotulo,
        "data_inicio": dt_inicio.date().isoformat(),
        "data_fim": dt_fim.date().isoformat(),
    }

    cache.set(cache_key, resultado, 60)
    return resultado


def obter_serie_temporal_projeto(
    projeto: ProjetoSite,
    periodo: str = "30d",
    data_inicio: str | None = None,
    data_fim: str | None = None,
    versao: int | None = None,
) -> list[dict[str, Any]]:
    """Gera dados agregados para gráfico temporal de evolução diária ou horária."""
    dt_inicio, dt_fim, _ = resolver_intervalo_datas(periodo, data_inicio, data_fim)
    tz = timezone.get_current_timezone()

    cache_key = (
        f"ana_serie:{projeto.id}:{periodo}:{dt_inicio.date()}:{dt_fim.date()}:{versao or 'all'}"
    )
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    qs = EventoAnalitico.objects.filter(
        projeto=projeto,
        ocorrido_em__gte=dt_inicio,
        ocorrido_em__lte=dt_fim,
    )
    if versao:
        qs = qs.filter(publicacao__numero_versao=versao)

    pontos = []
    if periodo == "hoje":
        # Agrupa por hora (0 a 23)
        eventos = list(qs.values("ocorrido_em", "tipo_evento"))
        mapa_horas = {h: {"visualizacoes": 0, "cliques": 0, "nfc": 0, "qr": 0} for h in range(24)}
        for e in eventos:
            hora = timezone.localtime(e["ocorrido_em"], tz).hour
            t = e["tipo_evento"]
            if t == EventoAnalitico.TipoEvento.PAGE_VIEW:
                mapa_horas[hora]["visualizacoes"] += 1
            elif t == EventoAnalitico.TipoEvento.COMPONENT_CLICK:
                mapa_horas[hora]["cliques"] += 1
            elif t == EventoAnalitico.TipoEvento.SMARTLINK_NFC:
                mapa_horas[hora]["nfc"] += 1
            elif t == EventoAnalitico.TipoEvento.SMARTLINK_QR:
                mapa_horas[hora]["qr"] += 1

        for h in range(24):
            pontos.append(
                {
                    "rotulo": f"{h:02d}:00",
                    "visualizacoes": mapa_horas[h]["visualizacoes"],
                    "cliques": mapa_horas[h]["cliques"],
                    "nfc": mapa_horas[h]["nfc"],
                    "qr": mapa_horas[h]["qr"],
                }
            )
    else:
        # Agrupa por dia no intervalo
        dias = (dt_fim.date() - dt_inicio.date()).days + 1
        mapa_dias = {
            (dt_inicio.date() + timedelta(days=i)): {
                "visualizacoes": 0,
                "cliques": 0,
                "nfc": 0,
                "qr": 0,
            }
            for i in range(dias)
        }

        eventos = list(qs.values("ocorrido_em", "tipo_evento"))
        for e in eventos:
            dia = timezone.localtime(e["ocorrido_em"], tz).date()
            if dia in mapa_dias:
                t = e["tipo_evento"]
                if t == EventoAnalitico.TipoEvento.PAGE_VIEW:
                    mapa_dias[dia]["visualizacoes"] += 1
                elif t == EventoAnalitico.TipoEvento.COMPONENT_CLICK:
                    mapa_dias[dia]["cliques"] += 1
                elif t == EventoAnalitico.TipoEvento.SMARTLINK_NFC:
                    mapa_dias[dia]["nfc"] += 1
                elif t == EventoAnalitico.TipoEvento.SMARTLINK_QR:
                    mapa_dias[dia]["qr"] += 1

        for dia, contagens in sorted(mapa_dias.items()):
            pontos.append(
                {
                    "rotulo": dia.strftime("%d/%m"),
                    "data_iso": dia.isoformat(),
                    "visualizacoes": contagens["visualizacoes"],
                    "cliques": contagens["cliques"],
                    "nfc": contagens["nfc"],
                    "qr": contagens["qr"],
                }
            )

    cache.set(cache_key, pontos, 60)
    return pontos


def obter_origens_acesso_projeto(
    projeto: ProjetoSite,
    periodo: str = "30d",
    data_inicio: str | None = None,
    data_fim: str | None = None,
    versao: int | None = None,
) -> dict[str, Any]:
    """Calcula a distribuição de origens de acesso (NFC, QR Code e Direto)."""
    dt_inicio, dt_fim, _ = resolver_intervalo_datas(periodo, data_inicio, data_fim)

    cache_key = (
        f"ana_orig:{projeto.id}:{periodo}:{dt_inicio.date()}:{dt_fim.date()}:{versao or 'all'}"
    )
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    qs = EventoAnalitico.objects.filter(
        projeto=projeto,
        ocorrido_em__gte=dt_inicio,
        ocorrido_em__lte=dt_fim,
    )
    if versao:
        qs = qs.filter(publicacao__numero_versao=versao)

    contagens = qs.values("origem").annotate(total=Count("id"))
    mapa = {
        EventoAnalitico.OrigemAcesso.NFC: 0,
        EventoAnalitico.OrigemAcesso.QR: 0,
        EventoAnalitico.OrigemAcesso.DIRETO_DESCONHECIDO: 0,
    }

    # Considera também os acessos registrados via smartlinks NFC e QR
    for row in contagens:
        orig = row["origem"]
        if orig in mapa:
            mapa[orig] += row["total"]

    nfc = qs.filter(tipo_evento=EventoAnalitico.TipoEvento.SMARTLINK_NFC).count()
    qr = qs.filter(tipo_evento=EventoAnalitico.TipoEvento.SMARTLINK_QR).count()
    direto = qs.filter(
        tipo_evento=EventoAnalitico.TipoEvento.PAGE_VIEW,
        origem=EventoAnalitico.OrigemAcesso.DIRETO_DESCONHECIDO,
    ).count()

    total = nfc + qr + direto
    resultado = {
        "nfc": nfc,
        "nfc_pct": round((nfc / total) * 100, 1) if total > 0 else 0.0,
        "qr": qr,
        "qr_pct": round((qr / total) * 100, 1) if total > 0 else 0.0,
        "direto": direto,
        "direto_pct": round((direto / total) * 100, 1) if total > 0 else 0.0,
        "total": total,
    }

    cache.set(cache_key, resultado, 60)
    return resultado


def obter_top_componentes_projeto(
    projeto: ProjetoSite,
    periodo: str = "30d",
    data_inicio: str | None = None,
    data_fim: str | None = None,
    versao: int | None = None,
    limite: int = 10,
) -> list[dict[str, Any]]:
    """Retorna os componentes que mais receberam cliques no período."""
    dt_inicio, dt_fim, _ = resolver_intervalo_datas(periodo, data_inicio, data_fim)

    cache_key = (
        f"ana_top:{projeto.id}:{periodo}:{dt_inicio.date()}:{dt_fim.date()}:{versao or 'all'}"
    )
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    qs = EventoAnalitico.objects.filter(
        projeto=projeto,
        tipo_evento=EventoAnalitico.TipoEvento.COMPONENT_CLICK,
        ocorrido_em__gte=dt_inicio,
        ocorrido_em__lte=dt_fim,
    )
    if versao:
        qs = qs.filter(publicacao__numero_versao=versao)

    total_pageviews = EventoAnalitico.objects.filter(
        projeto=projeto,
        tipo_evento=EventoAnalitico.TipoEvento.PAGE_VIEW,
        ocorrido_em__gte=dt_inicio,
        ocorrido_em__lte=dt_fim,
    ).count()

    # Mapeamento de rótulos amigáveis
    ROTULOS_COMPONENTES = {
        "WHATSAPP": "WhatsApp",
        "TELEFONE": "Telefone",
        "EMAIL": "E-mail",
        "WEBSITE": "Website",
        "REDES_SOCIAIS": "Redes Sociais",
        "AGENDAMENTO_EXTERNO": "Agendamento Online",
        "MAPA": "Localização / Mapa",
        "BOTAO": "Botão de Ação",
        "SERVICOS": "Serviços",
    }

    agrupados = (
        qs.values("tipo_componente", "subitem_id")
        .annotate(total=Count("id"))
        .order_by("-total")[:limite]
    )

    ranking = []
    for item in agrupados:
        tipo_comp = item["tipo_componente"] or "OUTRO"
        subitem = item["subitem_id"]
        rotulo = ROTULOS_COMPONENTES.get(tipo_comp, tipo_comp.capitalize())
        if subitem:
            rotulo = f"{rotulo} ({subitem.capitalize()})"

        total_cliques = item["total"]
        taxa = round((total_cliques / total_pageviews) * 100, 1) if total_pageviews > 0 else 0.0

        ranking.append(
            {
                "tipo_componente": tipo_comp,
                "subitem_id": subitem or "",
                "rotulo": rotulo,
                "total": total_cliques,
                "taxa_aproximada": taxa,
            }
        )

    cache.set(cache_key, ranking, 60)
    return ranking


def obter_metricas_smart_links_projeto(
    projeto: ProjetoSite,
    periodo: str = "30d",
    data_inicio: str | None = None,
    data_fim: str | None = None,
) -> list[dict[str, Any]]:
    """Retorna a contagem de acessos separada por cada tag física ou QR Code individual."""
    dt_inicio, dt_fim, _ = resolver_intervalo_datas(periodo, data_inicio, data_fim)

    links = projeto.links_inteligentes.all().order_by("-criado_em")
    qs = EventoAnalitico.objects.filter(
        projeto=projeto,
        link_inteligente__isnull=False,
        ocorrido_em__gte=dt_inicio,
        ocorrido_em__lte=dt_fim,
    )

    contagens_map = {
        row["link_inteligente"]: row["total"]
        for row in qs.values("link_inteligente").annotate(total=Count("id"))
    }

    resultado = []
    for lk in links:
        total = contagens_map.get(lk.id, 0)
        resultado.append(
            {
                "id": lk.id,
                "uuid": str(lk.uuid),
                "nome": lk.nome,
                "tipo": lk.tipo,
                "tipo_display": lk.get_tipo_display(),
                "tipo_midia": lk.get_tipo_midia_fisica_display(),
                "token_mascarado": lk.token_mascarado(),
                "status": lk.status,
                "total_acessos": total,
            }
        )

    # Ordena por total de acessos decrescente
    resultado.sort(key=lambda x: x["total_acessos"], reverse=True)
    return resultado


def obter_metricas_link(link: LinkInteligente) -> dict[str, Any]:
    """Retorna métricas de acesso de um Link Inteligente específico em diferentes janelas de tempo."""
    tz = timezone.get_current_timezone()
    hoje = timezone.localtime(timezone.now(), tz).date()

    dt_hoje_ini = datetime.combine(hoje, time.min, tzinfo=tz)
    dt_7d_ini = datetime.combine(hoje - timedelta(days=6), time.min, tzinfo=tz)
    dt_30d_ini = datetime.combine(hoje - timedelta(days=29), time.min, tzinfo=tz)

    qs = EventoAnalitico.objects.filter(link_inteligente=link)

    hoje_count = qs.filter(ocorrido_em__gte=dt_hoje_ini).count()
    dias_7_count = qs.filter(ocorrido_em__gte=dt_7d_ini).count()
    dias_30_count = qs.filter(ocorrido_em__gte=dt_30d_ini).count()
    total_count = qs.count()

    return {
        "hoje": hoje_count,
        "dias_7": dias_7_count,
        "dias_30": dias_30_count,
        "total": total_count,
    }


def obter_metricas_globais(
    periodo: str = "30d",
    data_inicio: str | None = None,
    data_fim: str | None = None,
) -> dict[str, Any]:
    """Retorna estatísticas e rankings globais da plataforma para o dashboard administrativo geral."""
    dt_inicio, dt_fim, rotulo = resolver_intervalo_datas(periodo, data_inicio, data_fim)

    cache_key = f"ana_glob:{periodo}:{dt_inicio.date()}:{dt_fim.date()}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    qs = EventoAnalitico.objects.filter(
        ocorrido_em__gte=dt_inicio,
        ocorrido_em__lte=dt_fim,
    )

    agregado = qs.aggregate(
        total_visualizacoes=Count("id", filter=Q(tipo_evento=EventoAnalitico.TipoEvento.PAGE_VIEW)),
        total_nfc=Count("id", filter=Q(tipo_evento=EventoAnalitico.TipoEvento.SMARTLINK_NFC)),
        total_qr=Count("id", filter=Q(tipo_evento=EventoAnalitico.TipoEvento.SMARTLINK_QR)),
        total_cliques=Count("id", filter=Q(tipo_evento=EventoAnalitico.TipoEvento.COMPONENT_CLICK)),
    )

    total_vis = agregado["total_visualizacoes"] or 0
    total_cliques = agregado["total_cliques"] or 0
    ctr_global = round((total_cliques / total_vis) * 100, 1) if total_vis > 0 else 0.0

    # Top BioSites por Visualizações
    top_projetos_vis = (
        qs.filter(tipo_evento=EventoAnalitico.TipoEvento.PAGE_VIEW)
        .values("projeto__id", "projeto__uuid", "projeto__nome", "projeto__slug")
        .annotate(total=Count("id"))
        .order_by("-total")[:5]
    )

    # Top BioSites por NFC
    top_projetos_nfc = (
        qs.filter(tipo_evento=EventoAnalitico.TipoEvento.SMARTLINK_NFC)
        .values("projeto__id", "projeto__uuid", "projeto__nome", "projeto__slug")
        .annotate(total=Count("id"))
        .order_by("-total")[:5]
    )

    # Top BioSites por QR
    top_projetos_qr = (
        qs.filter(tipo_evento=EventoAnalitico.TipoEvento.SMARTLINK_QR)
        .values("projeto__id", "projeto__uuid", "projeto__nome", "projeto__slug")
        .annotate(total=Count("id"))
        .order_by("-total")[:5]
    )

    # Top BioSites por Cliques
    top_projetos_cliques = (
        qs.filter(tipo_evento=EventoAnalitico.TipoEvento.COMPONENT_CLICK)
        .values("projeto__id", "projeto__uuid", "projeto__nome", "projeto__slug")
        .annotate(total=Count("id"))
        .order_by("-total")[:5]
    )

    resultado = {
        "total_visualizacoes": total_vis,
        "total_nfc": agregado["total_nfc"] or 0,
        "total_qr": agregado["total_qr"] or 0,
        "total_cliques": total_cliques,
        "ctr_global": ctr_global,
        "periodo": periodo,
        "periodo_rotulo": rotulo,
        "data_inicio": dt_inicio.date().isoformat(),
        "data_fim": dt_fim.date().isoformat(),
        "top_visualizacoes": list(top_projetos_vis),
        "top_nfc": list(top_projetos_nfc),
        "top_qr": list(top_projetos_qr),
        "top_cliques": list(top_projetos_cliques),
    }

    cache.set(cache_key, resultado, 60)
    return resultado
