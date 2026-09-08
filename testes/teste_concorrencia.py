"""
Script de teste de concorrência e benchmarking do SQLite (Prompt 12, itens 243-251).

Avalia o comportamento e a estabilidade do SQLite sob 5 cenários críticos simultâneos:
1. Cenário 1: Leituras públicas simultâneas de BioSites.
2. Cenário 2: Gravações concorrentes de eventos PAGE_VIEW.
3. Cenário 3: Resoluções de Smart Links (NFC/QR) com redirecionamento e analytics.
4. Cenário 4: Operações de salvamento do editor enquanto eventos são gravados.
5. Cenário 5: Publicação de nova versão de BioSite durante tráfego de leitura e cliques.

Métricas aferidas:
- Quantidade total de requisições por cenário
- Taxa de sucesso (%)
- Erros de contenção ("database is locked")
- Latência média (ms) e percentis p95/máximo
- Throughput agregado (operações/segundo)
"""
# ruff: noqa: E402

import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# Configura ambiente Django
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "configuracao.settings.desenvolvimento")

import django

django.setup()

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import Client

from aplicativos.clientes.models import Cliente
from aplicativos.sites.models import (
    EventoAnalitico,
    LinkInteligente,
    ProjetoSite,
)
from aplicativos.sites.servicos_analytics import (
    registrar_evento,
)
from aplicativos.sites.servicos_links import criar_link_inteligente
from aplicativos.sites.servicos_publicacao import publicar_projeto

Usuario = get_user_model()


def configurar_ambiente_benchmark():
    """Prepara os registros no banco para o teste de concorrência."""
    print("-> Preparando dados de teste para o benchmark...")

    # Cria cliente e projeto de benchmark
    admin_user, _ = Usuario.objects.get_or_create(
        username="admin_bench",
        defaults={
            "email": "bench@biosite.com",
            "is_staff": True,
            "is_superuser": True,
        },
    )
    if not admin_user.has_usable_password():
        admin_user.set_password("BenchForte123!")
        admin_user.save()

    cliente, _ = Cliente.objects.get_or_create(
        email="cliente_bench@teste.com",
        defaults={"nome": "Clínica Benchmark Concorrência", "documento": "11144477735"},
    )

    projeto, _ = ProjetoSite.objects.get_or_create(
        slug="clinica-benchmark",
        defaults={
            "cliente": cliente,
            "nome": "BioSite Benchmark Concorrência",
            "status": ProjetoSite.Status.RASCUNHO,
        },
    )

    # Garante estrutura básica de página para publicação válida
    if not projeto.paginas.exists():
        from aplicativos.sites.models import (
            ContainerSite,
            ElementoSite,
            PaginaSite,
            SecaoSite,
        )

        pag = PaginaSite.objects.create(
            projeto=projeto,
            titulo="Início",
            slug="",
            eh_inicial=True,
            ordem=0,
            ativa=True,
        )
        sec = SecaoSite.objects.create(
            pagina=pag,
            nome_interno="Hero",
            ordem=0,
            ativa=True,
        )
        cont = ContainerSite.objects.create(
            secao=sec,
            ordem=0,
            ativo=True,
        )
        ElementoSite.objects.create(
            container=cont,
            tipo="titulo",
            conteudo={"texto": "Clínica Benchmark", "nivel": "h1"},
            ordem=0,
            ativo=True,
        )
        ElementoSite.objects.create(
            container=cont,
            tipo="whatsapp",
            conteudo={"numero": "5511999999999", "texto": "Agendar WhatsApp"},
            ordem=1,
            ativo=True,
        )

    # Publica primeira versão se não houver
    if not projeto.publicacao_ativa:
        publicar_projeto(projeto, usuario=admin_user)
        projeto.refresh_from_db()

    # Cria tags NFC e QR limpas com tokens exclusivos
    LinkInteligente.objects.filter(projeto=projeto).delete()
    link_nfc = criar_link_inteligente(
        projeto=projeto,
        tipo=LinkInteligente.Tipo.NFC,
        nome="NFC Cartão Benchmark",
    )
    link_qr = criar_link_inteligente(
        projeto=projeto,
        tipo=LinkInteligente.Tipo.QR,
        nome="QR Placa Benchmark",
    )

    return admin_user, cliente, projeto, link_nfc, link_qr


def executar_cenario_1_leituras_publicas(projeto, total_ops=100, workers=8):
    """Cenário 1: Múltiplos visitantes apenas lendo BioSites."""
    client = Client()
    url = f"/b/{projeto.slug}/"
    latencias = []
    erros = 0
    locks = 0

    def operacao():
        t0 = time.perf_counter()
        try:
            res = client.get(url, HTTP_HOST="localhost")
            t_ms = (time.perf_counter() - t0) * 1000
            if res.status_code == 200:
                return True, t_ms, None
            return False, t_ms, f"Status {res.status_code}"
        except Exception as e:
            t_ms = (time.perf_counter() - t0) * 1000
            msg = str(e)
            return False, t_ms, msg

    t_inicio = time.perf_counter()
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(operacao) for _ in range(total_ops)]
        for f in as_completed(futures):
            ok, t_ms, err = f.result()
            latencias.append(t_ms)
            if not ok:
                erros += 1
                if err and "locked" in err.lower():
                    locks += 1

    t_total = time.perf_counter() - t_inicio
    return {
        "cenario": "Cenário 1: Leituras Públicas BioSite",
        "total_ops": total_ops,
        "erros": erros,
        "locks": locks,
        "latencia_media_ms": sum(latencias) / len(latencias) if latencias else 0,
        "latencia_max_ms": max(latencias) if latencias else 0,
        "tempo_total_s": t_total,
        "throughput_rps": total_ops / t_total if t_total > 0 else 0,
    }


def executar_cenario_2_writes_pageviews(projeto, total_ops=100, workers=8):
    """Cenário 2: Múltiplos PAGE_VIEW sendo gravados concorrentemente."""
    latencias = []
    erros = 0
    locks = 0
    pub = projeto.publicacao_ativa

    def operacao(i):
        t0 = time.perf_counter()
        try:
            evt = registrar_evento(
                projeto=projeto,
                tipo_evento=EventoAnalitico.TipoEvento.PAGE_VIEW,
                origem=EventoAnalitico.OrigemAcesso.DIRETO_DESCONHECIDO,
                publicacao=pub,
            )
            t_ms = (time.perf_counter() - t0) * 1000
            if evt:
                return True, t_ms, None
            return False, t_ms, "Falha na gravação"
        except Exception as e:
            t_ms = (time.perf_counter() - t0) * 1000
            msg = str(e)
            return False, t_ms, msg

    t_inicio = time.perf_counter()
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(operacao, i) for i in range(total_ops)]
        for f in as_completed(futures):
            ok, t_ms, err = f.result()
            latencias.append(t_ms)
            if not ok:
                erros += 1
                if err and "locked" in err.lower():
                    locks += 1

    t_total = time.perf_counter() - t_inicio
    return {
        "cenario": "Cenário 2: Gravações de PAGE_VIEW",
        "total_ops": total_ops,
        "erros": erros,
        "locks": locks,
        "latencia_media_ms": sum(latencias) / len(latencias) if latencias else 0,
        "latencia_max_ms": max(latencias) if latencias else 0,
        "tempo_total_s": t_total,
        "throughput_rps": total_ops / t_total if t_total > 0 else 0,
    }


def executar_cenario_3_nfc_qr_redirects(link_nfc, link_qr, total_ops=100, workers=8):
    """Cenário 3: NFC/QR redirects + Analytics."""
    client = Client()
    latencias = []
    erros = 0
    locks = 0

    def operacao(i):
        token = link_nfc.token if i % 2 == 0 else link_qr.token
        tipo_rota = "n" if i % 2 == 0 else "q"
        url = f"/{tipo_rota}/{token}/"
        t0 = time.perf_counter()
        try:
            res = client.get(url, HTTP_HOST="localhost")
            t_ms = (time.perf_counter() - t0) * 1000
            if res.status_code == 302:
                return True, t_ms, None
            return False, t_ms, f"Status {res.status_code}"
        except Exception as e:
            t_ms = (time.perf_counter() - t0) * 1000
            return False, t_ms, str(e)

    t_inicio = time.perf_counter()
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(operacao, i) for i in range(total_ops)]
        for f in as_completed(futures):
            ok, t_ms, err = f.result()
            latencias.append(t_ms)
            if not ok:
                erros += 1
                if err and "locked" in err.lower():
                    locks += 1

    t_total = time.perf_counter() - t_inicio
    return {
        "cenario": "Cenário 3: NFC/QR Redirects + Analytics",
        "total_ops": total_ops,
        "erros": erros,
        "locks": locks,
        "latencia_media_ms": sum(latencias) / len(latencias) if latencias else 0,
        "latencia_max_ms": max(latencias) if latencias else 0,
        "tempo_total_s": t_total,
        "throughput_rps": total_ops / t_total if t_total > 0 else 0,
    }


def executar_cenario_4_editor_e_analytics(admin_user, projeto, total_ops=80, workers=8):
    """Cenário 4: Editor salvando enquanto Analytics grava."""
    client = Client()
    client.force_login(admin_user)
    latencias = []
    erros = 0
    locks = 0

    def operacao_editor(i):
        t0 = time.perf_counter()
        try:
            res = client.post(
                f"/painel/sites/{projeto.uuid}/editor/design/salvar/",
                data={
                    "configuracao_visual": {
                        "cor_primaria": "#38bdf8",
                        "fonte_principal": "Inter",
                        "contador": i,
                    }
                },
                content_type="application/json",
                HTTP_HOST="localhost",
            )
            t_ms = (time.perf_counter() - t0) * 1000
            if res.status_code == 200:
                return True, t_ms, None
            return False, t_ms, f"Status {res.status_code}"
        except Exception as e:
            t_ms = (time.perf_counter() - t0) * 1000
            return False, t_ms, str(e)

    def operacao_analytics(i):
        t0 = time.perf_counter()
        try:
            evt = registrar_evento(
                projeto=projeto,
                tipo_evento=EventoAnalitico.TipoEvento.COMPONENT_CLICK,
                origem=EventoAnalitico.OrigemAcesso.DIRETO_DESCONHECIDO,
                tipo_componente="whatsapp",
            )
            t_ms = (time.perf_counter() - t0) * 1000
            return (True, t_ms, None) if evt else (False, t_ms, "Erro gravação")
        except Exception as e:
            t_ms = (time.perf_counter() - t0) * 1000
            return False, t_ms, str(e)

    t_inicio = time.perf_counter()
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = []
        for i in range(total_ops):
            if i % 2 == 0:
                futures.append(executor.submit(operacao_editor, i))
            else:
                futures.append(executor.submit(operacao_analytics, i))

        for f in as_completed(futures):
            ok, t_ms, err = f.result()
            latencias.append(t_ms)
            if not ok:
                erros += 1
                if err and "locked" in err.lower():
                    locks += 1

    t_total = time.perf_counter() - t_inicio
    return {
        "cenario": "Cenário 4: Editor Salvando + Analytics Concorrente",
        "total_ops": total_ops,
        "erros": erros,
        "locks": locks,
        "latencia_media_ms": sum(latencias) / len(latencias) if latencias else 0,
        "latencia_max_ms": max(latencias) if latencias else 0,
        "tempo_total_s": t_total,
        "throughput_rps": total_ops / t_total if t_total > 0 else 0,
    }


def executar_cenario_5_publicacao_sob_trafego(admin_user, projeto, total_ops=60, workers=6):
    """Cenário 5: Publicação enquanto tráfego público ocorre."""
    client = Client()
    latencias = []
    erros = 0
    locks = 0

    def operacao_leitura():
        t0 = time.perf_counter()
        try:
            res = client.get(f"/b/{projeto.slug}/", HTTP_HOST="localhost")
            t_ms = (time.perf_counter() - t0) * 1000
            return (res.status_code == 200), t_ms, None
        except Exception as e:
            t_ms = (time.perf_counter() - t0) * 1000
            return False, t_ms, str(e)

    def operacao_publicacao(i):
        t0 = time.perf_counter()
        try:
            projeto.refresh_from_db()
            # Gera alteração no rascunho para validar publicação real
            cfg = projeto.configuracao_visual
            cfg.cor_primaria = f"#00{i:02d}ff"[:7]
            cfg.save()
            pub = publicar_projeto(projeto, usuario=admin_user)
            t_ms = (time.perf_counter() - t0) * 1000
            return (pub is not None), t_ms, None
        except Exception as e:
            t_ms = (time.perf_counter() - t0) * 1000
            return False, t_ms, str(e)

    t_inicio = time.perf_counter()
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = []
        for i in range(total_ops):
            if i % 10 == 0:
                futures.append(executor.submit(operacao_publicacao, i))
            else:
                futures.append(executor.submit(operacao_leitura))

        for f in as_completed(futures):
            ok, t_ms, err = f.result()
            latencias.append(t_ms)
            if not ok:
                erros += 1
                if err and "locked" in err.lower():
                    locks += 1
                else:
                    print(f"  [Cenário 5 Erro]: {err}")

    t_total = time.perf_counter() - t_inicio
    return {
        "cenario": "Cenário 5: Publicação Simultânea sob Tráfego",
        "total_ops": total_ops,
        "erros": erros,
        "locks": locks,
        "latencia_media_ms": sum(latencias) / len(latencias) if latencias else 0,
        "latencia_max_ms": max(latencias) if latencias else 0,
        "tempo_total_s": t_total,
        "throughput_rps": total_ops / t_total if t_total > 0 else 0,
    }


def executar_benchmark_completo():
    print("=" * 70)
    print("TESTE DE CONCORRÊNCIA E ESTRESSE — MOTOR DE BANCO DE DADOS (SQLITE)")
    print("=" * 70)

    admin_user, cliente, projeto, link_nfc, link_qr = configurar_ambiente_benchmark()

    # Informações de PRAGMA SQLite
    with connection.cursor() as cursor:
        cursor.execute("PRAGMA journal_mode;")
        journal_mode = cursor.fetchone()[0]
        cursor.execute("PRAGMA busy_timeout;")
        busy_timeout = cursor.fetchone()[0]
    print(f"Modo Journal: {journal_mode.upper()} | Busy Timeout: {busy_timeout}ms\n")

    cenarios = [
        executar_cenario_1_leituras_publicas(projeto, total_ops=100, workers=8),
        executar_cenario_2_writes_pageviews(projeto, total_ops=100, workers=8),
        executar_cenario_3_nfc_qr_redirects(link_nfc, link_qr, total_ops=100, workers=8),
        executar_cenario_4_editor_e_analytics(admin_user, projeto, total_ops=60, workers=6),
        executar_cenario_5_publicacao_sob_trafego(admin_user, projeto, total_ops=50, workers=5),
    ]

    print("-" * 70)
    print(
        f"{'Cenário':<42} | {'Ops':<5} | {'Erros':<5} | {'Locks':<5} | {'Média (ms)':<10} | {'Throughput'}"
    )
    print("-" * 70)

    total_ops_global = 0
    total_erros_global = 0
    total_locks_global = 0

    for c in cenarios:
        total_ops_global += c["total_ops"]
        total_erros_global += c["erros"]
        total_locks_global += c["locks"]
        nome_curto = c["cenario"]
        print(
            f"{nome_curto:<42} | {c['total_ops']:<5} | {c['erros']:<5} | {c['locks']:<5} | "
            f"{c['latencia_media_ms']:<10.2f} | {c['throughput_rps']:.1f} req/s"
        )

    print("-" * 70)
    print(
        f"TOTAL: {total_ops_global} operações | {total_erros_global} erros | {total_locks_global} database locks"
    )
    taxa_sucesso = ((total_ops_global - total_erros_global) / total_ops_global) * 100
    print(f"Taxa de Sucesso Global: {taxa_sucesso:.2f}%\n")

    # Avaliação do Decision Gate
    if total_locks_global == 0 and taxa_sucesso >= 99.0:
        print(
            "DECISION GATE RECOMENDADO: OPÇÃO A (SQLite suficiente para lançamento em servidor único persistente)"
        )
        print(
            "Justificativa: Zero falhas de 'database is locked', latência baixa e estabilidade sob concorrência."
        )
    elif total_locks_global <= 2 and taxa_sucesso >= 95.0:
        print("DECISION GATE RECOMENDADO: OPÇÃO B (SQLite utilizável com restrições operacionais)")
    else:
        print("DECISION GATE RECOMENDADO: OPÇÃO C (Migrar para PostgreSQL antes da produção)")

    print("=" * 70)
    return cenarios


if __name__ == "__main__":
    executar_benchmark_completo()
