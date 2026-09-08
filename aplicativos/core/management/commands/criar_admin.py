"""Comando operacional para criar ou redefinir o usuário administrador de desenvolvimento."""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Cria ou redefine o superusuário administrador (padrão: admin / admin)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--username",
            default="admin",
            help="Nome de usuário do administrador (padrão: admin)",
        )
        parser.add_argument(
            "--password",
            default="admin",
            help="Senha do administrador (padrão: admin)",
        )
        parser.add_argument(
            "--email",
            default="admin@biosite.com",
            help="E-mail do administrador (padrão: admin@biosite.com)",
        )

    def handle(self, *args, **options):
        username = options["username"]
        password = options["password"]
        email = options["email"]

        Usuario = get_user_model()
        user, created = Usuario.objects.get_or_create(
            username=username,
            defaults={"email": email, "is_staff": True, "is_superuser": True},
        )
        user.set_password(password)
        user.email = email
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        user.save()

        acao = "criado" if created else "atualizado"
        self.stdout.write(
            self.style.SUCCESS(
                f"Superusuário '{username}' {acao} com sucesso! Senha: '{password}'."
            )
        )
