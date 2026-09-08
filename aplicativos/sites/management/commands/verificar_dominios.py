"""
Comando de gerenciamento para auditoria e verificação de integridade dos domínios e subdomínios dos BioSites.

Uso:
    python manage.py verificar_dominios
"""

from collections import Counter

from django.core.management.base import BaseCommand
from django.utils import timezone

from aplicativos.sites.models import EnderecoSite, HistoricoEnderecoSite, ProjetoSite
from aplicativos.sites.validadores_dominios import (
    obter_subdominios_reservados,
    validar_formato_host,
)


class Command(BaseCommand):
    help = (
        "Audita integridade de hosts, múltiplos principais, domínios sem verificação e quarentenas."
    )

    def handle(self, *args, **options):
        self.stdout.write("Iniciando auditoria de domínios e resolução de host...")

        total_enderecos = EnderecoSite.objects.count()
        total_historico = HistoricoEnderecoSite.objects.count()

        if total_enderecos == 0:
            self.stdout.write(self.style.WARNING("Nenhum endereço cadastrado no banco de dados."))
            return

        erros = 0
        avisos = 0

        # 1. Checagem de Hosts duplicados
        hosts = list(EnderecoSite.objects.values_list("host", flat=True))
        contagem_hosts = Counter(hosts)
        duplicados = [h for h, count in contagem_hosts.items() if count > 1]
        if duplicados:
            erros += len(duplicados)
            self.stdout.write(
                self.style.ERROR(
                    f"CRÍTICO: Foram encontrados {len(duplicados)} hosts duplicados: {duplicados}"
                )
            )
        else:
            self.stdout.write(self.style.SUCCESS("[OK] Unicidade de hosts: 100% íntegra."))

        # 2. Checagem de Múltiplos Principais por Projeto
        projetos = ProjetoSite.objects.prefetch_related("enderecos").all()
        reservados = obter_subdominios_reservados()

        for proj in projetos:
            principais = [e for e in proj.enderecos.all() if e.principal]
            if len(principais) > 1:
                erros += 1
                self.stdout.write(
                    self.style.ERROR(
                        f"CRÍTICO: Projeto '{proj.nome}' ({proj.id}) possui {len(principais)} endereços principais: "
                        f"{[e.host for e in principais]}"
                    )
                )
            elif len(principais) == 0 and proj.esta_publicado():
                avisos += 1
                self.stdout.write(
                    self.style.WARNING(
                        f"AVISO: Projeto publicado '{proj.nome}' ({proj.id}) não possui endereço principal definido."
                    )
                )

            # 3. Validação de Subdomínios Reservados
            for end in proj.enderecos.all():
                if end.tipo == EnderecoSite.Tipo.SUBDOMINIO_PLATAFORMA and end.subdominio:
                    if end.subdominio.lower() in reservados:
                        erros += 1
                        self.stdout.write(
                            self.style.ERROR(
                                f"CRÍTICO: Endereço '{end.host}' utiliza subdomínio reservado proibido: '{end.subdominio}'"
                            )
                        )

                # 4. Formato de Host válido RFC 1035 / RFC 1123
                try:
                    validar_formato_host(end.host)
                except Exception as e:
                    erros += 1
                    self.stdout.write(
                        self.style.ERROR(f"CRÍTICO: Host com formato inválido '{end.host}': {e}")
                    )

                # 5. Domínio Personalizado ATIVO sem verificação
                if end.tipo == EnderecoSite.Tipo.DOMINIO_PERSONALIZADO:
                    if end.status == EnderecoSite.Status.ATIVO and not end.verificado_em:
                        erros += 1
                        self.stdout.write(
                            self.style.ERROR(
                                f"CRÍTICO: Domínio personalizado '{end.host}' está ATIVO mas não possui verificado_em."
                            )
                        )
                    if not end.token_verificacao:
                        avisos += 1
                        self.stdout.write(
                            self.style.WARNING(
                                f"AVISO: Domínio personalizado '{end.host}' não possui token de verificação gerado."
                            )
                        )

        # 6. Quarentena
        expirados = HistoricoEnderecoSite.objects.filter(reservado_ate__lte=timezone.now()).count()
        ativos_quarentena = total_historico - expirados

        self.stdout.write("\n--- Resumo da Auditoria ---")
        self.stdout.write(f"Total de Endereços Auditados: {total_enderecos}")
        self.stdout.write(
            f"  - Subdomínios da plataforma: {EnderecoSite.objects.filter(tipo=EnderecoSite.Tipo.SUBDOMINIO_PLATAFORMA).count()}"
        )
        self.stdout.write(
            f"  - Domínios personalizados: {EnderecoSite.objects.filter(tipo=EnderecoSite.Tipo.DOMINIO_PERSONALIZADO).count()}"
        )
        self.stdout.write(
            f"    - Ativos: {EnderecoSite.objects.filter(status=EnderecoSite.Status.ATIVO, tipo=EnderecoSite.Tipo.DOMINIO_PERSONALIZADO).count()}"
        )
        self.stdout.write(
            f"    - Verificados: {EnderecoSite.objects.filter(status=EnderecoSite.Status.VERIFICADO).count()}"
        )
        self.stdout.write(
            f"    - Pendentes: {EnderecoSite.objects.filter(status=EnderecoSite.Status.PENDENTE).count()}"
        )
        self.stdout.write(
            f"    - Erro: {EnderecoSite.objects.filter(status=EnderecoSite.Status.ERRO).count()}"
        )
        self.stdout.write(
            f"Quarentenas de Histórico: {total_historico} ({ativos_quarentena} ativas, {expirados} expiradas)"
        )

        if erros > 0:
            self.stdout.write(
                self.style.ERROR(
                    f"\nFalha na auditoria: {erros} erro(s) crítico(s) e {avisos} aviso(s) detectados."
                )
            )
        elif avisos > 0:
            self.stdout.write(
                self.style.WARNING(
                    f"\nAuditoria concluída com {avisos} aviso(s). Nenhum erro crítico encontrado."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    "\nAuditoria concluída com sucesso! Todos os domínios e hosts estão 100% íntegros."
                )
            )
