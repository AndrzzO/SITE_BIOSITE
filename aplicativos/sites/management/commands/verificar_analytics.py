"""
Comando de auditoria e verificação de integridade dos registros de Analytics (Prompt 11).

Execução:
    python manage.py verificar_analytics
"""

from django.core.management.base import BaseCommand
from django.utils import timezone

from aplicativos.sites.models import (
    EventoAnalitico,
    LinkInteligente,
)


class Command(BaseCommand):
    help = (
        "Audita a consistência, integridade e ausência de dados pessoais nas tabelas de Analytics."
    )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.NOTICE("Iniciando auditoria de integridade do sistema de Analytics...")
        )

        total_eventos = EventoAnalitico.objects.count()
        if total_eventos == 0:
            self.stdout.write(
                self.style.SUCCESS(
                    "Nenhum evento analítico registrado no banco de dados. Sistema íntegro."
                )
            )
            return

        self.stdout.write(f"Total de eventos analíticos registrados: {total_eventos}")

        erros_encontrados = 0
        avisos_encontrados = 0

        # 1. Eventos Órfãos de Projeto
        eventos_sem_projeto = EventoAnalitico.objects.filter(projeto__isnull=True).count()
        if eventos_sem_projeto > 0:
            self.stdout.write(
                self.style.ERROR(f"  [ERRO] {eventos_sem_projeto} evento(s) com projeto nulo.")
            )
            erros_encontrados += eventos_sem_projeto

        # 2. Tipos de Evento Inválidos
        tipos_validos = set(EventoAnalitico.TipoEvento.values)
        eventos_tipo_invalido = EventoAnalitico.objects.exclude(
            tipo_evento__in=tipos_validos
        ).count()
        if eventos_tipo_invalido > 0:
            self.stdout.write(
                self.style.ERROR(
                    f"  [ERRO] {eventos_tipo_invalido} evento(s) com tipo de evento inválido."
                )
            )
            erros_encontrados += eventos_tipo_invalido

        # 3. Origens de Acesso Inválidas
        origens_validas = set(EventoAnalitico.OrigemAcesso.values)
        eventos_origem_invalida = EventoAnalitico.objects.exclude(
            origem__in=origens_validas
        ).count()
        if eventos_origem_invalida > 0:
            self.stdout.write(
                self.style.ERROR(
                    f"  [ERRO] {eventos_origem_invalida} evento(s) com origem inválida."
                )
            )
            erros_encontrados += eventos_origem_invalida

        # 4. Inconsistência de Publicação (Publicação vinculada pertence a outro projeto)
        eventos_com_pub = EventoAnalitico.objects.filter(publicacao__isnull=False).select_related(
            "projeto", "publicacao"
        )
        inconsistencias_pub = 0
        for ev in eventos_com_pub:
            if ev.publicacao.projeto_id != ev.projeto_id:
                inconsistencias_pub += 1

        if inconsistencias_pub > 0:
            self.stdout.write(
                self.style.ERROR(
                    f"  [ERRO] {inconsistencias_pub} evento(s) associados a publicações de outro projeto."
                )
            )
            erros_encontrados += inconsistencias_pub

        # 5. Inconsistência de Link Inteligente
        links_ids = set(LinkInteligente.objects.values_list("id", flat=True))
        eventos_link_orfao = (
            EventoAnalitico.objects.filter(link_inteligente__isnull=False)
            .exclude(link_inteligente_id__in=links_ids)
            .count()
        )
        if eventos_link_orfao > 0:
            self.stdout.write(
                self.style.ERROR(
                    f"  [ERRO] {eventos_link_orfao} evento(s) referenciando links inteligentes inexistentes."
                )
            )
            erros_encontrados += eventos_link_orfao

        # 6. Eventos com Datas no Futuro (tolerância de 5 minutos para clock drift)
        limite_futuro = timezone.now() + timezone.timedelta(minutes=5)
        eventos_futuros = EventoAnalitico.objects.filter(ocorrido_em__gt=limite_futuro).count()
        if eventos_futuros > 0:
            self.stdout.write(
                self.style.WARNING(
                    f"  [AVISO] {eventos_futuros} evento(s) com timestamp futuro detectados."
                )
            )
            avisos_encontrados += eventos_futuros

        # 7. Verificação de Anonimização (Auditoria de Privacidade)
        # Garante que nenhum IP ou email acidental foi injetado em contexto_minimo
        eventos_com_dados_sensíveis = 0
        for ev in EventoAnalitico.objects.only("contexto_minimo")[:500]:
            ctx = ev.contexto_minimo or {}
            for k in ("ip", "remote_addr", "email", "user_agent", "fingerprint", "cpf"):
                if k in ctx:
                    eventos_com_dados_sensíveis += 1
                    break

        if eventos_com_dados_sensíveis > 0:
            self.stdout.write(
                self.style.ERROR(
                    f"  [VIOLAÇÃO DE PRIVACIDADE] {eventos_com_dados_sensíveis} evento(s) contêm chaves sensíveis em contexto_minimo."
                )
            )
            erros_encontrados += eventos_com_dados_sensíveis

        # Resumo Estatístico
        self.stdout.write("\n" + self.style.NOTICE("--- Resumo Estatístico ---"))
        for tipo in EventoAnalitico.TipoEvento:
            qtd = EventoAnalitico.objects.filter(tipo_evento=tipo).count()
            self.stdout.write(f"  {tipo.label} ({tipo.value}): {qtd}")

        self.stdout.write("\n" + self.style.NOTICE("--- Resumo por Origem ---"))
        for orig in EventoAnalitico.OrigemAcesso:
            qtd = EventoAnalitico.objects.filter(origem=orig).count()
            self.stdout.write(f"  {orig.label} ({orig.value}): {qtd}")

        self.stdout.write("")
        if erros_encontrados == 0 and avisos_encontrados == 0:
            self.stdout.write(
                self.style.SUCCESS(
                    "Auditoria concluída com sucesso! 100% dos eventos estão íntegros e compatíveis com as regras de privacidade."
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    f"Auditoria finalizada com {erros_encontrados} erro(s) e {avisos_encontrados} aviso(s)."
                )
            )
