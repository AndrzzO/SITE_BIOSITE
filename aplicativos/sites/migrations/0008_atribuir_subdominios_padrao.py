# Generated data migration to assign default platform subdomains to existing projects

import re
from django.conf import settings
from django.db import migrations


def atribuir_subdominios(apps, schema_editor):
    ProjetoSite = apps.get_model("sites", "ProjetoSite")
    EnderecoSite = apps.get_model("sites", "EnderecoSite")

    base_domain = getattr(settings, "PUBLIC_BASE_DOMAIN", "localhost").strip().lower()

    subdominios_reservados = {
        "www", "admin", "painel", "api", "static", "media", "assets", "cdn",
        "go", "nfc", "qr", "mail", "email", "smtp", "pop", "imap", "ftp",
        "health", "status", "support", "suporte", "app", "apps", "auth",
        "login", "logout", "test", "dev", "stage", "staging", "beta", "docs",
        "ajuda", "help", "billing", "pagamento", "checkout", "ws", "webhook",
        "sites", "biosite", "root", "ns1", "ns2", "dns"
    }

    sub_regex = re.compile(r"^[a-z0-9]([a-z0-9-]{1,61}[a-z0-9])?$")

    for projeto in ProjetoSite.objects.all():
        if EnderecoSite.objects.filter(projeto=projeto).exists():
            continue

        # Gera sugestão limpa a partir do slug
        slug_limpo = re.sub(r"[^a-z0-9-]", "-", str(projeto.slug or "site").lower()).strip("-")
        if len(slug_limpo) < 3:
            slug_limpo = f"site-{slug_limpo}"

        if not sub_regex.match(slug_limpo) or slug_limpo in subdominios_reservados:
            sub_base = f"site-{projeto.id}"
        else:
            sub_base = slug_limpo

        sub_final = sub_base
        tentativa = 1
        while EnderecoSite.objects.filter(host=f"{sub_final}.{base_domain}").exists():
            tentativa += 1
            sub_final = f"{sub_base}-{tentativa}"

        host_final = f"{sub_final}.{base_domain}"

        EnderecoSite.objects.create(
            projeto=projeto,
            host=host_final,
            subdominio=sub_final,
            tipo="subdominio_plataforma",
            status="ativo",
            principal=True,
            metadata={"migracao_inicial": True},
        )


def reverter_subdominios(apps, schema_editor):
    EnderecoSite = apps.get_model("sites", "EnderecoSite")
    EnderecoSite.objects.filter(metadata__has_key="migracao_inicial").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("sites", "0007_historicoenderecosite_enderecosite"),
    ]

    operations = [
        migrations.RunPython(atribuir_subdominios, reverter_subdominios),
    ]
