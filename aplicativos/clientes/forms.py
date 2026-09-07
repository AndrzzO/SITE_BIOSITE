"""Formulários para gestão de clientes comerciais."""

from django import forms
from django.utils.translation import gettext_lazy as _

from .models import Cliente


class ClienteForm(forms.ModelForm):
    """Formulário administrativo de cadastro e edição de clientes."""

    class Meta:
        model = Cliente
        fields = [
            "nome",
            "nome_fantasia",
            "email",
            "telefone",
            "whatsapp",
            "documento",
            "observacoes",
        ]
        error_messages = {
            "nome": {
                "required": _("O nome do cliente é obrigatório."),
            },
        }
        widgets = {
            "nome": forms.TextInput(
                attrs={
                    "class": "form-input",
                    "placeholder": "Ex: João Silva ou Empresa LTDA",
                    "autofocus": True,
                }
            ),
            "nome_fantasia": forms.TextInput(
                attrs={
                    "class": "form-input",
                    "placeholder": "Ex: Barbearia do João (opcional)",
                }
            ),
            "email": forms.EmailInput(
                attrs={
                    "class": "form-input",
                    "placeholder": "contato@cliente.com (opcional)",
                }
            ),
            "telefone": forms.TextInput(
                attrs={
                    "class": "form-input",
                    "placeholder": "(11) 3333-4444 (opcional)",
                }
            ),
            "whatsapp": forms.TextInput(
                attrs={
                    "class": "form-input",
                    "placeholder": "(11) 99999-8888 (opcional)",
                }
            ),
            "documento": forms.TextInput(
                attrs={
                    "class": "form-input",
                    "placeholder": "CPF ou CNPJ (opcional)",
                }
            ),
            "observacoes": forms.Textarea(
                attrs={
                    "class": "form-input",
                    "rows": 3,
                    "placeholder": "Anotações administrativas internas sobre o cliente...",
                }
            ),
        }

    def clean_nome(self) -> str:
        nome = self.cleaned_data.get("nome", "").strip()
        if not nome:
            raise forms.ValidationError(_("O nome do cliente é obrigatório."))
        return nome
