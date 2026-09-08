"""
Coleção dinâmica para ALLOWED_HOSTS com validação segura de hosts (Prompt 9).
"""

from collections.abc import Iterator

from django.core.cache import cache


class DynamicAllowedHosts(list):
    """
    Coleção iterável para o Django ALLOWED_HOSTS.

    Permite que o Django valide dinamicamente:
    1. Hosts estáticos configurados da plataforma (localhost, 127.0.0.1, base_domain, .base_domain).
    2. Domínios personalizados ATIVOS ou VERIFICADOS no banco de dados.

    Benefícios:
    - Zero reinicialização do Django ao cadastrar um novo domínio.
    - Bloqueia 100% de hosts desconhecidos ou maliciosos (HTTP 400 via DisallowedHost).
    - Não utiliza o atalho inseguro ALLOWED_HOSTS = ['*'].
    """

    def __init__(self, static_hosts=None):
        super().__init__(list(static_hosts or []))

    def __iter__(self) -> Iterator[str]:
        # 1. Produz os hosts estáticos da plataforma
        yield from super().__iter__()

        # 2. Produz o wildcard do domínio base da plataforma (ex: .localhost ou .seudominio.com)
        try:
            from django.conf import settings

            base_domain = getattr(settings, "PUBLIC_BASE_DOMAIN", None)
            if base_domain and base_domain not in ("*", ""):
                yield base_domain
                if not base_domain.startswith("."):
                    yield f".{base_domain}"
        except Exception:
            pass

        # 2. Produz os domínios personalizados ativos/verificados com cache rápido
        cached_custom_domains = cache.get("biosite:allowed_custom_hosts")
        if cached_custom_domains is None:
            try:
                from aplicativos.sites.models import EnderecoSite

                domains = list(
                    EnderecoSite.objects.filter(
                        tipo=EnderecoSite.Tipo.DOMINIO_PERSONALIZADO,
                        status__in=[EnderecoSite.Status.ATIVO, EnderecoSite.Status.VERIFICADO],
                    ).values_list("host", flat=True)
                )
                cache.set("biosite:allowed_custom_hosts", domains, 60)
                cached_custom_domains = domains
            except Exception:
                cached_custom_domains = []

        yield from cached_custom_domains

    def __contains__(self, item: object) -> bool:
        for pattern in self:
            if pattern == "*" or pattern == item:
                return True
        return False
