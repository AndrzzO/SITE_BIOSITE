"""Formulários para a administração e autenticação privada."""

from typing import Any

from django import forms
from django.contrib.auth import authenticate, get_user_model
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from .servicos.rate_limit import ServicoRateLimitLogin

Usuario = get_user_model()


class AutenticacaoAdministrativaForm(forms.Form):
    """
    Formulário de autenticação privada com suporte a login por Nome de Usuário ou E-mail.

    Segurança:
    - Retorna mensagem genérica de erro em qualquer falha de credenciais.
    - Integração transparente com o serviço de rate limiting para mitigar força bruta.
    - Suporta campos acessíveis com atributos HTML5 autocomplete.
    """

    identificador = forms.CharField(
        label=_("E-mail ou Usuário"),
        max_length=254,
        widget=forms.TextInput(
            attrs={
                "class": "form-input",
                "placeholder": "admin@biosite.com ou usuario",
                "autocomplete": "username",
                "autofocus": True,
            }
        ),
    )
    password = forms.CharField(
        label=_("Senha"),
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "class": "form-input",
                "placeholder": "Digite sua senha",
                "autocomplete": "current-password",
            }
        ),
    )

    def __init__(self, request=None, *args: Any, **kwargs: Any) -> None:
        self.request = request
        self.user_cache = None
        super().__init__(*args, **kwargs)

    def clean(self) -> dict[str, Any]:
        identificador = self.cleaned_data.get("identificador", "").strip()
        password = self.cleaned_data.get("password")

        if not identificador or not password:
            return self.cleaned_data

        ip = ServicoRateLimitLogin.obter_ip_cliente(self.request) if self.request else "127.0.0.1"

        # Verificar se está bloqueado por excesso de tentativas
        bloqueado, tempo_restante = ServicoRateLimitLogin.esta_bloqueado(ip, identificador)
        if bloqueado:
            minutos = max(1, (tempo_restante + 59) // 60)
            raise ValidationError(
                _(
                    "Muitas tentativas inválidas. Por segurança, tente novamente em %(minutos)s minuto(s)."
                ),
                code="rate_limited",
                params={"minutos": minutos},
            )

        # Resolução do usuário: por e-mail ou por username
        username_para_auth = identificador
        if "@" in identificador:
            usuario_encontrado = Usuario.objects.filter(email__iexact=identificador).first()
            if usuario_encontrado:
                username_para_auth = usuario_encontrado.get_username()

        # Autenticação oficial do Django
        user = authenticate(self.request, username=username_para_auth, password=password)

        if user is None:
            ServicoRateLimitLogin.registrar_falha(ip, identificador)
            raise ValidationError(
                _("Usuário ou senha inválidos."),
                code="invalid_login",
            )

        if not user.is_active:
            ServicoRateLimitLogin.registrar_falha(ip, identificador)
            raise ValidationError(
                _("Usuário ou senha inválidos."),
                code="inactive_account",
            )

        if not user.is_staff:
            ServicoRateLimitLogin.registrar_falha(ip, identificador)
            raise ValidationError(
                _("Usuário ou senha inválidos."),
                code="unauthorized_staff",
            )

        # Sucesso: limpa falhas acumuladas
        ServicoRateLimitLogin.limpar_falhas(ip, identificador)
        self.user_cache = user
        return self.cleaned_data

    def get_user(self):
        """Retorna o usuário autenticado."""
        return self.user_cache
