"""Data migration para garantir página inicial em projetos existentes de forma idempotente."""
from django.db import migrations


def criar_paginas_iniciais(apps, schema_editor):
    ProjetoSite = apps.get_model("sites", "ProjetoSite")
    PaginaSite = apps.get_model("sites", "PaginaSite")

    for projeto in ProjetoSite.objects.all():
        if not PaginaSite.objects.filter(projeto=projeto, eh_inicial=True).exists():
            PaginaSite.objects.create(
                projeto=projeto,
                titulo="Início",
                slug="inicio",
                ordem=10,
                eh_inicial=True,
                ativa=True,
            )


def reverter_paginas_iniciais(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("sites", "0002_containersite_elementosite_paginasite_secaosite_and_more"),
    ]

    operations = [
        migrations.RunPython(criar_paginas_iniciais, reverter_paginas_iniciais),
    ]
