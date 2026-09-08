"""
Comando de gerenciamento para auditoria e integridade de Links Inteligentes, Tags NFC e QR Codes (Prompt 10).

Uso:
    python manage.py verificar_links_inteligentes
"""

from collections import Counter

from django.core.management.base import BaseCommand

from aplicativos.sites.models import HistoricoVinculoTag, LinkInteligente, ProjetoSite


class Command(BaseCommand):
    help = "Audita integridade de tokens, links órfãos, tipos de mídia e históricos de vinculação."

    def handle(self, *args, **options):
        self.stdout.write("Iniciando auditoria de Links Inteligentes (Tags NFC e QR Codes)...")

        total_links = LinkInteligente.objects.count()
        total_historico = HistoricoVinculoTag.objects.count()

        if total_links == 0:
            self.stdout.write(
                self.style.WARNING("Nenhum link inteligente cadastrado no banco de dados.")
            )
            return

        erros = 0
        avisos = 0

        # 1. Unicidade de Tokens
        tokens = list(LinkInteligente.objects.values_list("token", flat=True))
        contagem = Counter(tokens)
        duplicados = [t for t, count in contagem.items() if count > 1]
        if duplicados:
            erros += len(duplicados)
            self.stdout.write(
                self.style.ERROR(
                    f"CRÍTICO: Foram encontrados {len(duplicados)} tokens duplicados: {duplicados}"
                )
            )
        else:
            self.stdout.write(self.style.SUCCESS("[OK] Unicidade de tokens: 100% íntegra."))

        # 2. Validação estrutural de cada Link
        tipos_validos = set(LinkInteligente.Tipo.values)
        status_validos = set(LinkInteligente.Status.values)

        links = LinkInteligente.objects.select_related("projeto", "projeto__cliente").all()

        for link in links:
            # Token não vazio e tamanho mínimo
            if not link.token or len(link.token) < 6:
                erros += 1
                self.stdout.write(
                    self.style.ERROR(
                        f"CRÍTICO: Link '{link.nome}' ({link.id}) possui token inválido ou muito curto: '{link.token}'"
                    )
                )

            # Tipo válido
            if link.tipo not in tipos_validos:
                erros += 1
                self.stdout.write(
                    self.style.ERROR(
                        f"CRÍTICO: Link '{link.nome}' ({link.id}) possui tipo desconhecido: '{link.tipo}'"
                    )
                )

            # Status válido
            if link.status not in status_validos:
                erros += 1
                self.stdout.write(
                    self.style.ERROR(
                        f"CRÍTICO: Link '{link.nome}' ({link.id}) possui status desconhecido: '{link.status}'"
                    )
                )

            # Vínculo com projeto
            if not link.projeto_id:
                erros += 1
                self.stdout.write(
                    self.style.ERROR(
                        f"CRÍTICO: Link '{link.nome}' ({link.id}) não possui projeto associado (órfão)."
                    )
                )
            else:
                proj = link.projeto
                if (
                    proj.status == ProjetoSite.Status.ARQUIVADO
                    and link.status == LinkInteligente.Status.ATIVO
                ):
                    avisos += 1
                    self.stdout.write(
                        self.style.WARNING(
                            f"AVISO: Link ativo '{link.nome}' ({link.id}) aponta para projeto arquivado: '{proj.nome}'"
                        )
                    )
                elif not proj.esta_publicado() and link.status == LinkInteligente.Status.ATIVO:
                    avisos += 1
                    self.stdout.write(
                        self.style.WARNING(
                            f"AVISO: Link ativo '{link.nome}' ({link.id}) aponta para projeto não publicado: '{proj.nome}'"
                        )
                    )

        # 3. Auditoria de Histórico de Vínculos
        historicos = HistoricoVinculoTag.objects.select_related("link", "projeto_novo").all()
        for h in historicos:
            if not h.link_id:
                erros += 1
                self.stdout.write(
                    self.style.ERROR(f"CRÍTICO: Registro de histórico {h.id} sem link associado.")
                )
            if not h.projeto_novo_id:
                erros += 1
                self.stdout.write(
                    self.style.ERROR(
                        f"CRÍTICO: Registro de histórico {h.id} sem novo projeto definido."
                    )
                )

        # 4. Resumo estatístico
        self.stdout.write("\n--- Resumo da Auditoria de Links Inteligentes ---")
        self.stdout.write(f"Total de Links Auditados: {total_links}")
        self.stdout.write(
            f"  - Tags NFC: {LinkInteligente.objects.filter(tipo=LinkInteligente.Tipo.NFC).count()}"
        )
        self.stdout.write(
            f"  - QR Codes: {LinkInteligente.objects.filter(tipo=LinkInteligente.Tipo.QR).count()}"
        )
        self.stdout.write(
            f"  - Ativos: {LinkInteligente.objects.filter(status=LinkInteligente.Status.ATIVO).count()}"
        )
        self.stdout.write(
            f"  - Inativos: {LinkInteligente.objects.filter(status=LinkInteligente.Status.INATIVO).count()}"
        )
        self.stdout.write(f"Histórico de Vínculos Auditados: {total_historico}")

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
                    "\nAuditoria concluída com sucesso! Todos os links inteligentes e tags NFC estão 100% íntegros."
                )
            )
