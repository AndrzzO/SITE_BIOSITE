"""Formulários para criação e edição de projetos de sites."""

from django import forms
from django.db import models
from django.utils.translation import gettext_lazy as _

from aplicativos.clientes.models import Cliente

from .models import ProjetoSite
from .servicos import gerar_slug_unico, validar_slug_permitido


class ProjetoSiteCriacaoForm(forms.ModelForm):
    """Formulário para criação de novos projetos de sites."""

    slug = forms.SlugField(
        label=_("Endereço / Slug"),
        max_length=100,
        required=False,
        help_text=_("Deixe em branco para gerar automaticamente a partir do nome."),
        widget=forms.TextInput(
            attrs={
                "class": "form-input",
                "placeholder": "ex: joao-silva (opcional)",
            }
        ),
    )

    class Meta:
        model = ProjetoSite
        fields = [
            "cliente",
            "nome",
            "slug",
            "tipo",
            "descricao_interna",
        ]
        widgets = {
            "cliente": forms.Select(attrs={"class": "form-input"}),
            "nome": forms.TextInput(
                attrs={
                    "class": "form-input",
                    "placeholder": "Ex: BioSite Oficial - Dr. André",
                    "autofocus": True,
                }
            ),
            "tipo": forms.Select(attrs={"class": "form-input"}),
            "descricao_interna": forms.Textarea(
                attrs={
                    "class": "form-input",
                    "rows": 3,
                    "placeholder": "Notas administrativas internas do projeto...",
                }
            ),
        }

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        # Exibe apenas clientes com status ATIVO para novos projetos
        self.fields["cliente"].queryset = Cliente.objects.filter(status=Cliente.Status.ATIVO)
        self.fields["cliente"].empty_label = "Selecione um cliente..."

    def clean_nome(self) -> str:
        nome = self.cleaned_data.get("nome", "").strip()
        if not nome:
            raise forms.ValidationError(_("O nome do projeto é obrigatório."))
        return nome

    def clean(self) -> dict:
        cleaned_data = super().clean()
        nome = cleaned_data.get("nome")
        slug = cleaned_data.get("slug")

        if nome:
            if slug:
                validar_slug_permitido(slug)

            # Gera slug único ou resolve colisões
            slug_final = gerar_slug_unico(
                nome=nome,
                slug_sugerido=slug if slug else None,
            )
            cleaned_data["slug"] = slug_final

        return cleaned_data


class ProjetoSiteEdicaoForm(forms.ModelForm):
    """Formulário para edição dos metadados de um projeto existente."""

    class Meta:
        model = ProjetoSite
        fields = [
            "cliente",
            "nome",
            "slug",
            "tipo",
            "descricao_interna",
        ]
        widgets = {
            "cliente": forms.Select(attrs={"class": "form-input"}),
            "nome": forms.TextInput(attrs={"class": "form-input"}),
            "slug": forms.TextInput(attrs={"class": "form-input"}),
            "tipo": forms.Select(attrs={"class": "form-input"}),
            "descricao_interna": forms.Textarea(attrs={"class": "form-input", "rows": 3}),
        }

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        # Permite manter o cliente atual ou selecionar outros ativos
        cliente_atual_id = self.instance.cliente_id if self.instance.pk else None
        self.fields["cliente"].queryset = Cliente.objects.filter(
            models.Q(status=Cliente.Status.ATIVO) | models.Q(id=cliente_atual_id)
        )

    def clean_nome(self) -> str:
        nome = self.cleaned_data.get("nome", "").strip()
        if not nome:
            raise forms.ValidationError(_("O nome do projeto é obrigatório."))
        return nome

    def clean_slug(self) -> str:
        slug = self.cleaned_data.get("slug", "").strip()
        if not slug:
            raise forms.ValidationError(_("O slug do projeto não pode ser vazio."))
        validar_slug_permitido(slug)

        # Checar duplicidade excluindo a própria instância
        duplicado = ProjetoSite.objects.filter(slug=slug).exclude(id=self.instance.id).exists()
        if duplicado:
            raise forms.ValidationError(
                _("Este endereço '%(slug)s' já está em uso por outro site. Escolha outro."),
                params={"slug": slug},
            )
        return slug
