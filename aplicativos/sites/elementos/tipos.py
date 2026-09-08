import html
import re
from typing import Any
from urllib.parse import quote, urlparse

from django.core.exceptions import ValidationError
from django.core.validators import EmailValidator
from django.utils.html import escape, format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from .base import DefinicaoElemento
from .icones import obter_svg_icone
from .registry import registro_elementos

_validador_email = EmailValidator()


# -----------------------------------------------------------------------------
# Elementos Básicos de Texto e Estrutura
# -----------------------------------------------------------------------------


@registro_elementos.registrar
class ElementoTitulo(DefinicaoElemento):
    identificador = "titulo"
    nome = _("Título")
    categoria = _("Texto")
    icone = "🏷️"

    NIVEIS_PERMITIDOS = frozenset({"h1", "h2", "h3", "h4", "h5", "h6", "p"})

    def conteudo_padrao(self) -> dict[str, Any]:
        return {
            "texto": "Título do BioSite",
            "nivel": "h2",
        }

    def estilos_padrao(self) -> dict[str, Any]:
        return {
            "base": {
                "alinhamento": "center",
                "tamanho_fonte": 26,
                "peso_fonte": "700",
                "cor_texto": "",  # vazio para herdar var(--cor-texto)
            },
            "desktop": {
                "tamanho_fonte": 32,
            },
        }

    def validar_conteudo(self, conteudo: dict[str, Any]) -> None:
        if not isinstance(conteudo, dict):
            raise ValidationError(_("Conteúdo inválido para o elemento Título."))

        texto = conteudo.get("texto", "")
        if not isinstance(texto, str) or not texto.strip():
            raise ValidationError(_("O campo 'texto' do Título é obrigatório."))

        texto_limpo = escape(texto.strip())
        if len(texto_limpo) > 300:
            raise ValidationError(_("O Título não pode exceder 300 caracteres."))

        conteudo["texto"] = texto_limpo

        nivel = conteudo.get("nivel", "h2")
        if nivel not in self.NIVEIS_PERMITIDOS:
            raise ValidationError(
                _("Nível de cabeçalho inválido: '%(nivel)s'."), params={"nivel": nivel}
            )

    def render(self, elemento: Any, contexto: dict[str, Any] | None = None) -> str:
        conteudo = elemento.conteudo or self.conteudo_padrao()
        nivel = conteudo.get("nivel", "h2")
        texto = html.unescape(str(conteudo.get("texto", "")))
        return format_html('<{0} class="elemento-titulo biosite-heading">{1}</{0}>', nivel, texto)


@registro_elementos.registrar
class ElementoTexto(DefinicaoElemento):
    identificador = "texto"
    nome = _("Parágrafo")
    categoria = _("Texto")
    icone = "📝"

    def conteudo_padrao(self) -> dict[str, Any]:
        return {
            "texto": "Descrição, biografia ou informações de contato do profissional ou negócio.",
        }

    def estilos_padrao(self) -> dict[str, Any]:
        return {
            "base": {
                "alinhamento": "center",
                "tamanho_fonte": 15,
                "cor_texto": "",  # herda var(--cor-texto-secundario)
            },
            "desktop": {},
        }

    def validar_conteudo(self, conteudo: dict[str, Any]) -> None:
        if not isinstance(conteudo, dict):
            raise ValidationError(_("Conteúdo inválido para o elemento Texto."))

        texto = conteudo.get("texto", "")
        if not isinstance(texto, str) or not texto.strip():
            raise ValidationError(_("O campo 'texto' do Parágrafo é obrigatório."))

        conteudo["texto"] = escape(texto.strip())

    def render(self, elemento: Any, contexto: dict[str, Any] | None = None) -> str:
        conteudo = elemento.conteudo or self.conteudo_padrao()
        texto = html.unescape(str(conteudo.get("texto", "")))
        return format_html('<p class="elemento-texto biosite-body">{}</p>', texto)


@registro_elementos.registrar
class ElementoAvatar(DefinicaoElemento):
    identificador = "avatar"
    nome = _("Foto de Perfil")
    categoria = _("Mídia")
    icone = "👤"

    FORMAS_PERMITIDAS = frozenset({"circulo", "arredondado", "quadrado"})

    def conteudo_padrao(self) -> dict[str, Any]:
        return {
            "url": "",
            "alt": "Foto de Perfil",
            "tamanho": 100,
            "forma": "circulo",
            "borda": True,
            "sombra": "suave",
        }

    def validar_conteudo(self, conteudo: dict[str, Any]) -> None:
        if not isinstance(conteudo, dict):
            raise ValidationError(_("Conteúdo inválido para Avatar."))

        url = conteudo.get("url", "")
        if url and isinstance(url, str):
            if url.lower().startswith("javascript:"):
                raise ValidationError(_("URL insegura para avatar."))

        forma = conteudo.get("forma", "circulo")
        if forma not in self.FORMAS_PERMITIDAS:
            raise ValidationError(_("Forma de avatar inválida."))

        tamanho = conteudo.get("tamanho", 100)
        if not isinstance(tamanho, (int, float)) or tamanho < 32 or tamanho > 300:
            raise ValidationError(_("Tamanho de avatar deve ser entre 32px e 300px."))

    def render(self, elemento: Any, contexto: dict[str, Any] | None = None) -> str:
        conteudo = elemento.conteudo or self.conteudo_padrao()
        url = escape(conteudo.get("url", ""))
        alt = escape(conteudo.get("alt", "Foto de Perfil"))
        tamanho = int(conteudo.get("tamanho", 100))
        forma = conteudo.get("forma", "circulo")
        classe_forma = f"avatar-{forma}"
        tem_borda = "avatar-borda" if conteudo.get("borda", True) else ""

        if not url:
            svg_placeholder = obter_svg_icone("usuario")
            return format_html(
                '<div class="elemento-avatar avatar-placeholder {} {}" style="width:{}px; height:{}px;" aria-label="{}">{}</div>',
                classe_forma,
                tem_borda,
                tamanho,
                tamanho,
                alt,
                svg_placeholder,
            )

        return format_html(
            '<div class="elemento-avatar-container">'
            '<img src="{}" alt="{}" class="elemento-avatar {} {}" style="width:{}px; height:{}px;" loading="lazy">'
            "</div>",
            url,
            alt,
            classe_forma,
            tem_borda,
            tamanho,
            tamanho,
        )


@registro_elementos.registrar
class ElementoBotao(DefinicaoElemento):
    identificador = "botao"
    nome = _("Botão de Ação")
    categoria = _("Ação")
    icone = "🔘"
    rastreavel = True
    categoria_analytics = "acao"
    rotulo_analytics = "Botão"

    PROTOCOLOS_PERMITIDOS = frozenset({"http", "https", "mailto", "tel", "whatsapp", "sms"})
    ESTILOS_BOTAO = frozenset({"solido", "outline", "ghost", "glass"})

    def conteudo_padrao(self) -> dict[str, Any]:
        return {
            "texto": "Clique Aqui",
            "url": "https://",
            "nova_aba": True,
            "estilo_visual": "solido",
            "largura_total": True,
            "icone_id": "seta_direita",
        }

    def estilos_padrao(self) -> dict[str, Any]:
        return {
            "base": {
                "alinhamento": "center",
                "tamanho_fonte": 16,
                "raio_borda": 12,
                "padding_topo": 14,
                "padding_baixo": 14,
            },
            "desktop": {},
        }

    def validar_conteudo(self, conteudo: dict[str, Any]) -> None:
        if not isinstance(conteudo, dict):
            raise ValidationError(_("Conteúdo inválido para o elemento Botão."))

        texto = conteudo.get("texto", "").strip()
        if not texto:
            raise ValidationError(_("O texto do botão é obrigatório."))

        if len(texto) > 100:
            raise ValidationError(_("O texto do botão não pode exceder 100 caracteres."))

        url = conteudo.get("url", "").strip()
        if url:
            url_lower = url.lower()
            if url_lower.startswith(("javascript:", "data:", "vbscript:")):
                raise ValidationError(
                    _("Protocolos de script perigosos (como 'javascript:') são proibidos.")
                )

            if not url_lower.startswith(("#", "/")):
                parsed = urlparse(url)
                if parsed.scheme and parsed.scheme.lower() not in self.PROTOCOLOS_PERMITIDOS:
                    raise ValidationError(
                        _("Protocolo de URL não permitido: '%(scheme)s'."),
                        params={"scheme": parsed.scheme},
                    )

    def render(self, elemento: Any, contexto: dict[str, Any] | None = None) -> str:
        conteudo = elemento.conteudo or self.conteudo_padrao()
        texto = escape(conteudo.get("texto", ""))
        url = escape(conteudo.get("url", "#"))
        target = (
            ' target="_blank" rel="noopener noreferrer"' if conteudo.get("nova_aba", True) else ""
        )
        estilo_visual = conteudo.get("estilo_visual", "solido")
        largura_total = "btn-full-width" if conteudo.get("largura_total", True) else ""
        icone_id = conteudo.get("icone_id")
        svg_icone = obter_svg_icone(icone_id) if icone_id else ""
        token_attr = self.obter_token_clique(elemento, contexto)

        return format_html(
            '<a href="{}" class="elemento-botao biosite-btn btn-{} {}"{}{}><span>{}</span>{}</a>',
            url,
            estilo_visual,
            largura_total,
            mark_safe(target),
            mark_safe(token_attr),
            texto,
            svg_icone,
        )


@registro_elementos.registrar
class ElementoImagem(DefinicaoElemento):
    identificador = "imagem"
    nome = _("Imagem")
    categoria = _("Mídia")
    icone = "🖼️"

    FITS_PERMITIDOS = frozenset({"cover", "contain", "fill", "none"})

    def conteudo_padrao(self) -> dict[str, Any]:
        return {
            "url": "",
            "alt_text": "Imagem ilustrativa",
            "link_url": "",
            "fit": "cover",
            "proporcao": "16/9",
            "decorativa": False,
        }

    def validar_conteudo(self, conteudo: dict[str, Any]) -> None:
        if not isinstance(conteudo, dict):
            raise ValidationError(_("Conteúdo inválido para o elemento Imagem."))

        url = conteudo.get("url", "")
        if url and isinstance(url, str):
            if url.lower().startswith("javascript:"):
                raise ValidationError(_("URL não permitida para imagem."))

        link = conteudo.get("link_url", "")
        if link and isinstance(link, str):
            if link.lower().startswith(("javascript:", "data:")):
                raise ValidationError(_("Link da imagem com protocolo inseguro."))

    def render(self, elemento: Any, contexto: dict[str, Any] | None = None) -> str:
        conteudo = elemento.conteudo or self.conteudo_padrao()
        url = escape(conteudo.get("url", ""))
        alt = (
            "" if conteudo.get("decorativa", False) else escape(conteudo.get("alt_text", "Imagem"))
        )
        aria_hidden = ' aria-hidden="true"' if conteudo.get("decorativa", False) else ""
        fit = conteudo.get("fit", "cover")
        link = escape(conteudo.get("link_url", ""))

        if not url:
            return format_html(
                '<div class="imagem-placeholder" aria-label="Imagem vazia">🖼️ Imagem</div>'
            )

        img_tag = format_html(
            '<img src="{}" alt="{}" class="elemento-imagem" style="object-fit: {};" loading="lazy"{}>',
            url,
            alt,
            fit,
            mark_safe(aria_hidden),
        )

        if link:
            return format_html(
                '<a href="{}" target="_blank" rel="noopener noreferrer" class="imagem-link">{}</a>',
                link,
                mark_safe(img_tag),
            )
        return img_tag


# -----------------------------------------------------------------------------
# Componentes Comerciais, Contato e Redes Sociais
# -----------------------------------------------------------------------------


@registro_elementos.registrar
class ElementoWhatsApp(DefinicaoElemento):
    identificador = "whatsapp"
    nome = _("Botão WhatsApp")
    categoria = _("Contato")
    icone = "💬"
    rastreavel = True
    categoria_analytics = "contato"
    rotulo_analytics = "WhatsApp"

    def conteudo_padrao(self) -> dict[str, Any]:
        return {
            "numero": "5511999999999",
            "texto": "Falar no WhatsApp",
            "mensagem": "Olá! Gostaria de mais informações.",
            "estilo_botao": "solido",  # "solido", "outline", "flutuante"
            "largura_total": True,
            "mostrar_icone": True,
        }

    def estilos_padrao(self) -> dict[str, Any]:
        return {
            "base": {
                "cor_fundo": "#25D366",
                "cor_texto": "#ffffff",
                "raio_borda": 12,
                "padding_topo": 14,
                "padding_baixo": 14,
                "peso_fonte": "600",
            },
            "desktop": {},
        }

    def validar_conteudo(self, conteudo: dict[str, Any]) -> None:
        if not isinstance(conteudo, dict):
            raise ValidationError(_("Conteúdo inválido para WhatsApp."))

        numero = str(conteudo.get("numero", "")).strip()
        digitos = re.sub(r"\D", "", numero)
        if not digitos or len(digitos) < 8:
            raise ValidationError(
                _("Número de WhatsApp inválido (deve conter pelo menos 8 dígitos).")
            )
        conteudo["numero"] = digitos

        texto = conteudo.get("texto", "").strip()
        if not texto:
            conteudo["texto"] = "Falar no WhatsApp"

    def render(self, elemento: Any, contexto: dict[str, Any] | None = None) -> str:
        conteudo = elemento.conteudo or self.conteudo_padrao()
        numero = re.sub(r"\D", "", str(conteudo.get("numero", "")))
        msg = str(conteudo.get("mensagem", ""))
        url = f"https://wa.me/{numero}"
        if msg:
            url += f"?text={quote(msg)}"

        texto = escape(conteudo.get("texto", "Falar no WhatsApp"))
        estilo = conteudo.get("estilo_botao", "solido")
        svg_icone = obter_svg_icone("whatsapp") if conteudo.get("mostrar_icone", True) else ""
        token_attr = self.obter_token_clique(elemento, contexto)

        if estilo == "flutuante":
            return format_html(
                '<a href="{}" target="_blank" rel="noopener noreferrer" class="biosite-whatsapp-flutuante" aria-label="{}"{}>'
                "{}<span>{}</span>"
                "</a>",
                url,
                texto,
                mark_safe(token_attr),
                svg_icone,
                texto,
            )

        largura_total = "btn-full-width" if conteudo.get("largura_total", True) else ""
        return format_html(
            '<a href="{}" target="_blank" rel="noopener noreferrer" class="elemento-botao biosite-btn btn-whatsapp {}"{}>{}<span>{}</span></a>',
            url,
            largura_total,
            mark_safe(token_attr),
            svg_icone,
            texto,
        )


@registro_elementos.registrar
class ElementoTelefone(DefinicaoElemento):
    identificador = "telefone"
    nome = _("Ligar por Telefone")
    categoria = _("Contato")
    icone = "📞"
    rastreavel = True
    categoria_analytics = "contato"
    rotulo_analytics = "Telefone"

    def conteudo_padrao(self) -> dict[str, Any]:
        return {
            "numero": "(11) 99999-9999",
            "texto": "Ligar Agora",
            "mostrar_icone": True,
            "largura_total": True,
        }

    def estilos_padrao(self) -> dict[str, Any]:
        return {
            "base": {
                "raio_borda": 12,
                "padding_topo": 14,
                "padding_baixo": 14,
                "peso_fonte": "600",
            },
            "desktop": {},
        }

    def validar_conteudo(self, conteudo: dict[str, Any]) -> None:
        if not isinstance(conteudo, dict):
            raise ValidationError(_("Conteúdo inválido para Telefone."))
        numero = str(conteudo.get("numero", "")).strip()
        if not re.search(r"\d", numero):
            raise ValidationError(_("Informe um número de telefone válido."))

    def render(self, elemento: Any, contexto: dict[str, Any] | None = None) -> str:
        conteudo = elemento.conteudo or self.conteudo_padrao()
        numero_raw = str(conteudo.get("numero", ""))
        clean_tel = re.sub(r"[^\d+]", "", numero_raw)
        texto = escape(conteudo.get("texto", "Ligar Agora"))
        svg_icone = obter_svg_icone("telefone") if conteudo.get("mostrar_icone", True) else ""
        largura_total = "btn-full-width" if conteudo.get("largura_total", True) else ""
        token_attr = self.obter_token_clique(elemento, contexto)

        return format_html(
            '<a href="tel:{}" class="elemento-botao biosite-btn btn-telefone {}"{}>{}<span>{}</span></a>',
            clean_tel,
            largura_total,
            mark_safe(token_attr),
            svg_icone,
            texto,
        )


@registro_elementos.registrar
class ElementoEmail(DefinicaoElemento):
    identificador = "email"
    nome = _("Enviar E-mail")
    categoria = _("Contato")
    icone = "✉️"
    rastreavel = True
    categoria_analytics = "contato"
    rotulo_analytics = "E-mail"

    def conteudo_padrao(self) -> dict[str, Any]:
        return {
            "email": "contato@meubiosite.com",
            "texto": "Enviar Mensagem por E-mail",
            "assunto": "Contato via BioSite",
            "mostrar_icone": True,
            "largura_total": True,
        }

    def estilos_padrao(self) -> dict[str, Any]:
        return {
            "base": {
                "raio_borda": 12,
                "padding_topo": 14,
                "padding_baixo": 14,
                "peso_fonte": "600",
            },
            "desktop": {},
        }

    def validar_conteudo(self, conteudo: dict[str, Any]) -> None:
        if not isinstance(conteudo, dict):
            raise ValidationError(_("Conteúdo inválido para E-mail."))
        email = str(conteudo.get("email", "")).strip()
        try:
            _validador_email(email)
        except ValidationError as err:
            raise ValidationError(_("Endereço de e-mail inválido.")) from err

    def render(self, elemento: Any, contexto: dict[str, Any] | None = None) -> str:
        conteudo = elemento.conteudo or self.conteudo_padrao()
        email = escape(conteudo.get("email", ""))
        assunto = quote(conteudo.get("assunto", ""))
        texto = escape(conteudo.get("texto", "Enviar E-mail"))
        url = f"mailto:{email}"
        if assunto:
            url += f"?subject={assunto}"
        svg_icone = obter_svg_icone("email") if conteudo.get("mostrar_icone", True) else ""
        largura_total = "btn-full-width" if conteudo.get("largura_total", True) else ""
        token_attr = self.obter_token_clique(elemento, contexto)

        return format_html(
            '<a href="{}" class="elemento-botao biosite-btn btn-email {}"{}>{}<span>{}</span></a>',
            url,
            largura_total,
            mark_safe(token_attr),
            svg_icone,
            texto,
        )


@registro_elementos.registrar
class ElementoWebsite(DefinicaoElemento):
    identificador = "website"
    nome = _("Link do Website")
    categoria = _("Contato")
    icone = "🌐"
    rastreavel = True
    categoria_analytics = "acao"
    rotulo_analytics = "Website"

    def conteudo_padrao(self) -> dict[str, Any]:
        return {
            "url": "https://meusite.com",
            "texto": "Acessar Nosso Site Oficial",
            "mostrar_icone": True,
            "largura_total": True,
        }

    def estilos_padrao(self) -> dict[str, Any]:
        return {
            "base": {
                "raio_borda": 12,
                "padding_topo": 14,
                "padding_baixo": 14,
                "peso_fonte": "600",
            },
            "desktop": {},
        }

    def validar_conteudo(self, conteudo: dict[str, Any]) -> None:
        if not isinstance(conteudo, dict):
            raise ValidationError(_("Conteúdo inválido para Website."))
        url = str(conteudo.get("url", "")).strip()
        if not url.startswith(("http://", "https://")):
            raise ValidationError(_("A URL deve iniciar com http:// ou https://."))

    def render(self, elemento: Any, contexto: dict[str, Any] | None = None) -> str:
        conteudo = elemento.conteudo or self.conteudo_padrao()
        url = escape(conteudo.get("url", "#"))
        texto = escape(conteudo.get("texto", "Acessar Website"))
        svg_icone = obter_svg_icone("website") if conteudo.get("mostrar_icone", True) else ""
        largura_total = "btn-full-width" if conteudo.get("largura_total", True) else ""
        token_attr = self.obter_token_clique(elemento, contexto)

        return format_html(
            '<a href="{}" target="_blank" rel="noopener noreferrer" class="elemento-botao biosite-btn btn-website {}"{}>{}<span>{}</span></a>',
            url,
            largura_total,
            mark_safe(token_attr),
            svg_icone,
            texto,
        )


@registro_elementos.registrar
class ElementoRedesSociais(DefinicaoElemento):
    identificador = "redes_sociais"
    nome = _("Redes Sociais")
    categoria = _("Social")
    icone = "📱"
    rastreavel = True
    categoria_analytics = "social"
    rotulo_analytics = "Redes Sociais"

    REDES_SUPORTADAS = frozenset(
        {"instagram", "facebook", "tiktok", "linkedin", "youtube", "twitter_x", "whatsapp"}
    )

    def conteudo_padrao(self) -> dict[str, Any]:
        return {
            "itens": [
                {"rede": "instagram", "url": "https://instagram.com/perfil", "rotulo": "Instagram"},
                {"rede": "whatsapp", "url": "https://wa.me/5511999999999", "rotulo": "WhatsApp"},
                {"rede": "linkedin", "url": "https://linkedin.com/in/perfil", "rotulo": "LinkedIn"},
            ],
            "formato": "icones",  # "icones", "botoes", "grid"
        }

    def estilos_padrao(self) -> dict[str, Any]:
        return {
            "base": {
                "alinhamento": "center",
                "padding_topo": 8,
                "padding_baixo": 8,
            },
            "desktop": {},
        }

    def validar_conteudo(self, conteudo: dict[str, Any]) -> None:
        if not isinstance(conteudo, dict):
            raise ValidationError(_("Conteúdo inválido para Redes Sociais."))
        itens = conteudo.get("itens", [])
        if not isinstance(itens, list):
            raise ValidationError(_("A lista de redes sociais deve ser uma lista."))

        for item in itens:
            rede = item.get("rede", "").lower()
            if rede not in self.REDES_SUPORTADAS:
                raise ValidationError(
                    _("Rede social '%(rede)s' não suportada."), params={"rede": rede}
                )
            url = item.get("url", "").strip()
            if url and not url.startswith(("http://", "https://")):
                raise ValidationError(_("URLs das redes devem começar com http:// ou https://."))

    def render(self, elemento: Any, contexto: dict[str, Any] | None = None) -> str:
        conteudo = elemento.conteudo or self.conteudo_padrao()
        itens = conteudo.get("itens", [])
        formato = conteudo.get("formato", "icones")

        botoes_html = []
        for item in itens:
            rede = item.get("rede", "instagram")
            url = escape(item.get("url", "#"))
            rotulo = escape(item.get("rotulo", rede.capitalize()))
            svg = obter_svg_icone(rede)
            token_attr = self.obter_token_clique(elemento, contexto, subitem_id=rede)

            if formato == "botoes":
                botoes_html.append(
                    format_html(
                        '<a href="{}" target="_blank" rel="noopener noreferrer" class="social-btn social-btn-full" aria-label="{}"{}>{}<span>{}</span></a>',
                        url,
                        rotulo,
                        mark_safe(token_attr),
                        svg,
                        rotulo,
                    )
                )
            else:
                botoes_html.append(
                    format_html(
                        '<a href="{}" target="_blank" rel="noopener noreferrer" class="social-icon-btn" aria-label="{}" title="{}"{}>{}</a>',
                        url,
                        rotulo,
                        rotulo,
                        mark_safe(token_attr),
                        svg,
                    )
                )

        classe_container = f"social-container formato-{formato}"
        return format_html(
            '<div class="elemento-redes-sociais {}">{}</div>',
            classe_container,
            mark_safe("".join(botoes_html)),
        )


@registro_elementos.registrar
class ElementoAgendamentoExterno(DefinicaoElemento):
    identificador = "agendamento_externo"
    nome = _("Agendamento Externo")
    categoria = _("Comercial")
    icone = "📅"
    rastreavel = True
    categoria_analytics = "agenda"
    rotulo_analytics = "Agendamento"

    def conteudo_padrao(self) -> dict[str, Any]:
        return {
            "texto": "📅 Agendar Atendimento Online",
            "url": "https://calendar.google.com/",
            "plataforma": "google_calendar",
            "nova_aba": True,
            "largura_total": True,
        }

    def estilos_padrao(self) -> dict[str, Any]:
        return {
            "base": {
                "raio_borda": 12,
                "padding_topo": 14,
                "padding_baixo": 14,
                "peso_fonte": "600",
            },
            "desktop": {},
        }

    def validar_conteudo(self, conteudo: dict[str, Any]) -> None:
        if not isinstance(conteudo, dict):
            raise ValidationError(_("Conteúdo inválido para Agendamento."))
        url = str(conteudo.get("url", "")).strip()
        if not url.startswith("https://"):
            raise ValidationError(_("A URL de agendamento deve utilizar conexão segura HTTPS."))

    def render(self, elemento: Any, contexto: dict[str, Any] | None = None) -> str:
        conteudo = elemento.conteudo or self.conteudo_padrao()
        url = escape(conteudo.get("url", "#"))
        texto = escape(conteudo.get("texto", "Agendar Atendimento"))
        svg_icone = obter_svg_icone("calendario")
        largura_total = "btn-full-width" if conteudo.get("largura_total", True) else ""
        token_attr = self.obter_token_clique(elemento, contexto)

        return format_html(
            '<a href="{}" target="_blank" rel="noopener noreferrer" class="elemento-botao biosite-btn btn-agendamento {}"{}>'
            "{}<span>{}</span>"
            "</a>",
            url,
            largura_total,
            mark_safe(token_attr),
            svg_icone,
            texto,
        )


@registro_elementos.registrar
class ElementoMapa(DefinicaoElemento):
    identificador = "mapa"
    nome = _("Localização / Mapa")
    categoria = _("Comercial")
    icone = "📍"
    rastreavel = True
    categoria_analytics = "mapa"
    rotulo_analytics = "Localização"

    def conteudo_padrao(self) -> dict[str, Any]:
        return {
            "endereco": "Av. Paulista, 1000 - Bela Vista, São Paulo - SP",
            "texto": "📍 Ver Localização no Mapa",
            "url_personalizada": "",
            "largura_total": True,
        }

    def estilos_padrao(self) -> dict[str, Any]:
        return {
            "base": {
                "raio_borda": 12,
                "padding_topo": 14,
                "padding_baixo": 14,
                "peso_fonte": "600",
            },
            "desktop": {},
        }

    def validar_conteudo(self, conteudo: dict[str, Any]) -> None:
        if not isinstance(conteudo, dict):
            raise ValidationError(_("Conteúdo inválido para Mapa."))
        endereco = conteudo.get("endereco", "").strip()
        url_custom = conteudo.get("url_personalizada", "").strip()
        if not endereco and not url_custom:
            raise ValidationError(_("Informe o endereço ou o link personalizado do Google Maps."))

    def render(self, elemento: Any, contexto: dict[str, Any] | None = None) -> str:
        conteudo = elemento.conteudo or self.conteudo_padrao()
        url_custom = conteudo.get("url_personalizada", "").strip()
        endereco = conteudo.get("endereco", "").strip()

        if url_custom:
            url_mapa = escape(url_custom)
        else:
            url_mapa = f"https://www.google.com/maps/search/?api=1&query={quote(endereco)}"

        texto = escape(conteudo.get("texto", "Como Chegar"))
        svg_icone = obter_svg_icone("mapa")
        largura_total = "btn-full-width" if conteudo.get("largura_total", True) else ""
        token_attr = self.obter_token_clique(elemento, contexto)

        return format_html(
            '<div class="elemento-mapa-wrapper">'
            '<a href="{}" target="_blank" rel="noopener noreferrer" class="elemento-botao biosite-btn btn-mapa {}"{}>'
            "{}<span>{}</span>"
            "</a>"
            "</div>",
            url_mapa,
            largura_total,
            mark_safe(token_attr),
            svg_icone,
            texto,
        )


@registro_elementos.registrar
class ElementoServicos(DefinicaoElemento):
    identificador = "servicos"
    nome = _("Lista de Serviços")
    categoria = _("Comercial")
    icone = "💼"
    rastreavel = True
    categoria_analytics = "servico"
    rotulo_analytics = "Serviços"

    def conteudo_padrao(self) -> dict[str, Any]:
        return {
            "itens": [
                {
                    "titulo": "Consultoria Individual",
                    "descricao": "Atendimento personalizado de 1 hora com direcionamento estratégico.",
                    "preco": "R$ 250,00",
                    "link_cta": "https://wa.me/5511999999999",
                    "texto_cta": "Contratar",
                },
                {
                    "titulo": "Pacote Completo de Soluções",
                    "descricao": "Acompanhamento integral com entrega de relatórios e suporte dedicado.",
                    "preco": "R$ 800,00",
                    "link_cta": "https://wa.me/5511999999999",
                    "texto_cta": "Contratar",
                },
            ],
            "layout": "cards",  # "cards", "compacto"
        }

    def estilos_padrao(self) -> dict[str, Any]:
        return {
            "base": {
                "padding_topo": 12,
                "padding_baixo": 12,
            },
            "desktop": {},
        }

    def validar_conteudo(self, conteudo: dict[str, Any]) -> None:
        if not isinstance(conteudo, dict):
            raise ValidationError(_("Conteúdo inválido para Serviços."))
        itens = conteudo.get("itens", [])
        if not isinstance(itens, list):
            raise ValidationError(_("A lista de serviços deve ser uma lista."))
        if len(itens) > 20:
            raise ValidationError(_("Máximo de 20 serviços por bloco."))

        for s in itens:
            if not s.get("titulo", "").strip():
                raise ValidationError(_("Cada serviço deve ter um título."))

    def render(self, elemento: Any, contexto: dict[str, Any] | None = None) -> str:
        conteudo = elemento.conteudo or self.conteudo_padrao()
        itens = conteudo.get("itens", [])
        layout = conteudo.get("layout", "cards")

        cards_html = []
        for idx_s, s in enumerate(itens):
            titulo = escape(s.get("titulo", ""))
            desc = escape(s.get("descricao", ""))
            preco = escape(s.get("preco", ""))
            link = escape(s.get("link_cta", ""))
            txt_cta = escape(s.get("texto_cta", "Solicitar"))
            token_attr = self.obter_token_clique(
                elemento, contexto, subitem_id=f"servico_{idx_s + 1}"
            )

            preco_badge = f'<span class="servico-preco">{preco}</span>' if preco else ""
            cta_btn = (
                f'<a href="{link}" target="_blank" rel="noopener noreferrer" class="servico-cta"{token_attr}>{txt_cta}</a>'
                if link
                else ""
            )

            cards_html.append(
                format_html(
                    '<div class="servico-card">'
                    '<div class="servico-header">'
                    '<h4 class="servico-titulo">{}</h4>'
                    "{}"
                    "</div>"
                    '<p class="servico-descricao">{}</p>'
                    "{}"
                    "</div>",
                    titulo,
                    mark_safe(preco_badge),
                    desc,
                    mark_safe(cta_btn),
                )
            )

        return format_html(
            '<div class="elemento-servicos layout-{}">{}</div>',
            layout,
            mark_safe("".join(cards_html)),
        )


@registro_elementos.registrar
class ElementoGaleria(DefinicaoElemento):
    identificador = "galeria"
    nome = _("Galeria de Fotos")
    categoria = _("Mídia")
    icone = "📸"

    def conteudo_padrao(self) -> dict[str, Any]:
        return {
            "imagens": [
                {"url": "", "alt": "Foto 1"},
                {"url": "", "alt": "Foto 2"},
                {"url": "", "alt": "Foto 3"},
            ],
            "layout": "grid",  # "grid", "carrossel"
            "colunas": 2,
        }

    def estilos_padrao(self) -> dict[str, Any]:
        return {
            "base": {
                "padding_topo": 12,
                "padding_baixo": 12,
            },
            "desktop": {},
        }

    def validar_conteudo(self, conteudo: dict[str, Any]) -> None:
        if not isinstance(conteudo, dict):
            raise ValidationError(_("Conteúdo inválido para Galeria."))
        imagens = conteudo.get("imagens", [])
        if not isinstance(imagens, list):
            raise ValidationError(_("A galeria deve conter uma lista de imagens."))
        if len(imagens) > 24:
            raise ValidationError(_("Máximo de 24 imagens por galeria."))

    def render(self, elemento: Any, contexto: dict[str, Any] | None = None) -> str:
        conteudo = elemento.conteudo or self.conteudo_padrao()
        imagens = conteudo.get("imagens", [])
        layout = conteudo.get("layout", "grid")
        colunas = conteudo.get("colunas", 2)

        imgs_html = []
        for idx, img_item in enumerate(imagens):
            url = escape(img_item.get("url", ""))
            alt = escape(img_item.get("alt", f"Foto {idx + 1}"))
            if url:
                imgs_html.append(
                    format_html(
                        '<div class="galeria-item">'
                        '<img src="{}" alt="{}" class="galeria-img" loading="lazy">'
                        "</div>",
                        url,
                        alt,
                    )
                )
            else:
                imgs_html.append(
                    format_html(
                        '<div class="galeria-item galeria-placeholder">'
                        "<span>📸 Foto {}</span>"
                        "</div>",
                        idx + 1,
                    )
                )

        classe_layout = f"galeria-{layout} colunas-{colunas}"
        return format_html(
            '<div class="elemento-galeria {}">{}</div>',
            classe_layout,
            mark_safe("".join(imgs_html)),
        )


@registro_elementos.registrar
class ElementoDivisor(DefinicaoElemento):
    identificador = "divisor"
    nome = _("Divisor de Linha")
    categoria = _("Layout")
    icone = "➖"

    def conteudo_padrao(self) -> dict[str, Any]:
        return {
            "estilo": "solid",  # "solid", "dashed", "dotted"
            "espessura": 1,
            "largura": "100%",  # "25%", "50%", "75%", "100%"
            "cor": "",  # vazio para herdar var(--cor-secundaria) ou borda
            "espacamento": 16,
        }

    def validar_conteudo(self, conteudo: dict[str, Any]) -> None:
        if not isinstance(conteudo, dict):
            raise ValidationError(_("Conteúdo inválido para Divisor."))

    def render(self, elemento: Any, contexto: dict[str, Any] | None = None) -> str:
        conteudo = elemento.conteudo or self.conteudo_padrao()
        estilo = conteudo.get("estilo", "solid")
        espessura = int(conteudo.get("espessura", 1))
        largura = conteudo.get("largura", "100%")
        espacamento = int(conteudo.get("espacamento", 16))
        cor = conteudo.get("cor") or "var(--cor-superficie, #e2e8f0)"

        style_attr = (
            f"border: none; border-top: {espessura}px {estilo} {cor}; "
            f"width: {largura}; margin: {espacamento}px auto;"
        )

        return format_html(
            '<hr class="elemento-divisor" style="{}" aria-hidden="true">', mark_safe(style_attr)
        )


@registro_elementos.registrar
class ElementoEspacador(DefinicaoElemento):
    identificador = "espacador"
    nome = _("Espaçador")
    categoria = _("Layout")
    icone = "↕️"

    def conteudo_padrao(self) -> dict[str, Any]:
        return {
            "altura": 24,
        }

    def validar_conteudo(self, conteudo: dict[str, Any]) -> None:
        if not isinstance(conteudo, dict):
            raise ValidationError(_("Conteúdo inválido para Espaçador."))
        altura = conteudo.get("altura", 24)
        if not isinstance(altura, (int, float)) or altura < 4 or altura > 300:
            raise ValidationError(_("A altura do espaçador deve ser entre 4px e 300px."))

    def render(self, elemento: Any, contexto: dict[str, Any] | None = None) -> str:
        conteudo = elemento.conteudo or self.conteudo_padrao()
        altura = int(conteudo.get("altura", 24))
        return format_html(
            '<div class="elemento-espacador" style="height: {}px;" aria-hidden="true"></div>',
            altura,
        )


@registro_elementos.registrar
class ElementoIcone(DefinicaoElemento):
    identificador = "icone"
    nome = _("Ícone")
    categoria = _("Mídia")
    icone = "⭐"

    def conteudo_padrao(self) -> dict[str, Any]:
        return {
            "icone": "estrela",
        }

    def validar_conteudo(self, conteudo: dict[str, Any]) -> None:
        if not isinstance(conteudo, dict):
            raise ValidationError(_("Conteúdo inválido para Ícone."))
        icone = conteudo.get("icone", "").strip()
        if not icone:
            raise ValidationError(_("O identificador do ícone é obrigatório."))

    def render(self, elemento: Any, contexto: dict[str, Any] | None = None) -> str:
        conteudo = elemento.conteudo or self.conteudo_padrao()
        icone_id = conteudo.get("icone", "estrela")
        svg = obter_svg_icone(icone_id)
        return format_html('<span class="elemento-icone" aria-hidden="true">{}</span>', svg)


# -----------------------------------------------------------------------------
# Novos Elementos do Canvas Livre (Google Sites + Canva + Paint)
# -----------------------------------------------------------------------------


@registro_elementos.registrar
class ElementoVideo(DefinicaoElemento):
    identificador = "video"
    nome = _("Vídeo")
    categoria = _("Mídia")
    icone = "🎬"

    def conteudo_padrao(self) -> dict[str, Any]:
        return {
            "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "tipo_origem": "youtube",  # youtube, vimeo, url
            "autoplay": False,
            "muted": True,
            "loop": False,
            "controls": True,
            "raio_borda": 8,
        }

    def validar_conteudo(self, conteudo: dict[str, Any]) -> None:
        if not isinstance(conteudo, dict):
            raise ValidationError(_("Conteúdo inválido para Vídeo."))
        url = str(conteudo.get("url", "")).strip()
        if not url:
            raise ValidationError(_("A URL do vídeo é obrigatória."))

    def _extrair_youtube_id(self, url: str) -> str | None:
        padrao = r"(?:v=|\/|youtu\.be\/|embed\/)([a-zA-Z0-9_-]{11})"
        match = re.search(padrao, url)
        return match.group(1) if match else None

    def _extrair_vimeo_id(self, url: str) -> str | None:
        padrao = r"vimeo\.com\/(?:video\/)?([0-9]+)"
        match = re.search(padrao, url)
        return match.group(1) if match else None

    def render(self, elemento: Any, contexto: dict[str, Any] | None = None) -> str:
        conteudo = elemento.conteudo or self.conteudo_padrao()
        url = str(conteudo.get("url", "")).strip()
        autoplay = 1 if conteudo.get("autoplay") else 0
        muted = 1 if conteudo.get("muted") else 0
        loop = 1 if conteudo.get("loop") else 0
        controls = 1 if conteudo.get("controls", True) else 0
        raio = int(conteudo.get("raio_borda", 8))

        # YouTube
        yt_id = self._extrair_youtube_id(url)
        if yt_id:
            embed_url = (
                f"https://www.youtube-nocookie.com/embed/{yt_id}?"
                f"autoplay={autoplay}&mute={muted}&loop={loop}&controls={controls}"
            )
            return format_html(
                '<div class="elemento-video-wrapper" style="position:relative;width:100%;padding-bottom:56.25%;height:0;overflow:hidden;border-radius:{}px;">'
                '<iframe src="{}" style="position:absolute;top:0;left:0;width:100%;height:100%;border:0;" '
                'allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" '
                'allowfullscreen loading="lazy"></iframe></div>',
                raio,
                embed_url,
            )

        # Vimeo
        vimeo_id = self._extrair_vimeo_id(url)
        if vimeo_id:
            embed_url = (
                f"https://player.vimeo.com/video/{vimeo_id}?"
                f"autoplay={autoplay}&muted={muted}&loop={loop}"
            )
            return format_html(
                '<div class="elemento-video-wrapper" style="position:relative;width:100%;padding-bottom:56.25%;height:0;overflow:hidden;border-radius:{}px;">'
                '<iframe src="{}" style="position:absolute;top:0;left:0;width:100%;height:100%;border:0;" '
                'allow="autoplay; fullscreen; picture-in-picture" allowfullscreen loading="lazy"></iframe></div>',
                raio,
                embed_url,
            )

        # MP4 URL direta
        if url.endswith(".mp4") or url.endswith(".webm"):
            attrs = ["playsinline"]
            if autoplay:
                attrs.append("autoplay")
            if muted:
                attrs.append("muted")
            if loop:
                attrs.append("loop")
            if controls:
                attrs.append("controls")
            attrs_str = " ".join(attrs)
            return format_html(
                '<div class="elemento-video-wrapper" style="width:100%;border-radius:{}px;overflow:hidden;">'
                '<video src="{}" style="width:100%;display:block;" {} preload="metadata"></video></div>',
                raio,
                url,
                mark_safe(attrs_str),
            )

        # Fallback para URL genérica embed
        return format_html(
            '<div class="elemento-video-wrapper" style="position:relative;width:100%;padding-bottom:56.25%;height:0;overflow:hidden;border-radius:{}px;">'
            '<iframe src="{}" style="position:absolute;top:0;left:0;width:100%;height:100%;border:0;" '
            'allowfullscreen loading="lazy"></iframe></div>',
            raio,
            url,
        )


@registro_elementos.registrar
class ElementoForma(DefinicaoElemento):
    identificador = "forma"
    nome = _("Forma / Bloco")
    categoria = _("Estrutura")
    icone = "⬛"

    def conteudo_padrao(self) -> dict[str, Any]:
        return {
            "subtipo": "retangulo",  # "retangulo", "circulo", "cartao"
            "cor_fundo": "#38bdf8",
            "opacidade": 1.0,
            "cor_borda": "transparent",
            "largura_borda": 0,
            "raio_borda": 8,
            "sombra": "nenhuma",  # nenhuma, suave, media, forte
        }

    def validar_conteudo(self, conteudo: dict[str, Any]) -> None:
        if not isinstance(conteudo, dict):
            raise ValidationError(_("Conteúdo inválido para Forma."))

    def render(self, elemento: Any, contexto: dict[str, Any] | None = None) -> str:
        conteudo = elemento.conteudo or self.conteudo_padrao()
        subtipo = conteudo.get("subtipo", "retangulo")
        cor_fundo = conteudo.get("cor_fundo", "#38bdf8")
        opacidade = float(conteudo.get("opacidade", 1.0))
        cor_borda = conteudo.get("cor_borda", "transparent")
        largura_borda = int(conteudo.get("largura_borda", 0))
        raio_borda = int(conteudo.get("raio_borda", 8))

        if subtipo == "circulo":
            raio_borda = 9999

        mapa_sombras = {
            "nenhuma": "none",
            "suave": "0 2px 8px -2px rgba(0, 0, 0, 0.08)",
            "media": "0 6px 16px -4px rgba(0, 0, 0, 0.15)",
            "forte": "0 12px 28px -6px rgba(0, 0, 0, 0.25)",
        }
        sombra = mapa_sombras.get(str(conteudo.get("sombra", "nenhuma")), "none")

        style = (
            f"background-color: {cor_fundo}; opacity: {opacidade}; "
            f"border: {largura_borda}px solid {cor_borda}; "
            f"border-radius: {raio_borda}px; box-shadow: {sombra}; "
            f"width: 100%; height: 100%; min-height: 40px;"
        )

        return format_html('<div class="elemento-forma" style="{}"></div>', mark_safe(style))


@registro_elementos.registrar
class ElementoHtmlEmbed(DefinicaoElemento):
    identificador = "html_embed"
    nome = _("Código HTML / Embed")
    categoria = _("Avançado")
    icone = "💻"

    def conteudo_padrao(self) -> dict[str, Any]:
        return {
            "codigo_html": "<div style='padding:1rem;text-align:center;'>Bloco HTML Customizado</div>",
            "altura_px": 120,
        }

    def validar_conteudo(self, conteudo: dict[str, Any]) -> None:
        if not isinstance(conteudo, dict):
            raise ValidationError(_("Conteúdo inválido para HTML Embed."))
        codigo = conteudo.get("codigo_html", "")
        if len(str(codigo)) > 50000:
            raise ValidationError(_("O código HTML não pode exceder 50.000 caracteres."))

    def render(self, elemento: Any, contexto: dict[str, Any] | None = None) -> str:
        conteudo = elemento.conteudo or self.conteudo_padrao()
        codigo = str(conteudo.get("codigo_html", ""))
        altura = int(conteudo.get("altura_px", 120))

        # Isolamento absoluto via iframe sandbox com srcdoc
        # O iframe impede vazamento de CSS e protege cookies/localStorage do admin
        codigo_escapado = escape(codigo)
        return format_html(
            '<div class="elemento-html-embed" style="width:100%;overflow:hidden;min-height:{}px;">'
            '<iframe srcdoc="{}" sandbox="allow-scripts" '
            'style="width:100%;height:{}px;border:none;display:block;" loading="lazy"></iframe>'
            "</div>",
            altura,
            mark_safe(codigo_escapado),
            altura,
        )


@registro_elementos.registrar
class ElementoLogo(DefinicaoElemento):
    identificador = "logo"
    nome = _("Logo da Marca")
    categoria = _("Mídia")
    icone = "🏷️"

    def conteudo_padrao(self) -> dict[str, Any]:
        return {
            "url_imagem": "",
            "texto_alternativo": "Logo",
            "largura_px": 140,
            "link_url": "",
        }

    def validar_conteudo(self, conteudo: dict[str, Any]) -> None:
        if not isinstance(conteudo, dict):
            raise ValidationError(_("Conteúdo inválido para Logo."))

    def render(self, elemento: Any, contexto: dict[str, Any] | None = None) -> str:
        conteudo = elemento.conteudo or self.conteudo_padrao()
        url = conteudo.get("url_imagem", "").strip()
        alt = escape(conteudo.get("texto_alternativo", "Logo"))
        largura = int(conteudo.get("largura_px", 140))
        link = conteudo.get("link_url", "").strip()

        if url:
            tag_img = format_html(
                '<img src="{}" alt="{}" style="max-width:{}px;width:100%;height:auto;display:block;margin:0 auto;" loading="lazy">',
                url,
                alt,
                largura,
            )
        else:
            tag_img = format_html(
                '<div style="font-size:1.25rem;font-weight:800;letter-spacing:-0.5px;text-align:center;">{}</div>',
                alt,
            )

        if link:
            return format_html(
                '<a href="{}" target="_blank" rel="noopener noreferrer" style="text-decoration:none;display:inline-block;">{}</a>',
                link,
                tag_img,
            )
        return tag_img
