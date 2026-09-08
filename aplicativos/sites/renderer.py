"""Motor de renderização compartilhada do BioSite (Editor, Preview e Público).

Garante fidelidade visual idêntica entre o canvas de edição e a visualização final,
respeitando a filosofia Mobile-First e isolamento de CSS.
"""

import copy
from typing import Any

from django.utils.html import escape, format_html
from django.utils.safestring import SafeString, mark_safe

from .elementos import RegistroElementos
from .models import ContainerSite, ElementoSite, PaginaSite, SecaoSite


class RenderizadorBioSite:
    """
    Renderizador universal da árvore estrutural do BioSite.

    Suporta dois modos operacionais:
    - 'editor': Renderiza o HTML incluindo alças de drag, atributos de seleção (data-id) e controles de edição.
    - 'preview' / 'publico': Renderiza HTML semântico limpo, sem nenhum controle administrativo.
    """

    def __init__(self, modo: str = "preview") -> None:
        self.modo = modo
        self.eh_editor = modo == "editor"

    def converter_estilos_para_css(self, estilos: dict[str, Any], seletor: str) -> str:
        """
        Converte o dicionário de estilos mobile-first em declarações CSS.

        Gera regras padrão (mobile/base) e @media query para overrides em desktop.
        """
        if not isinstance(estilos, dict):
            return ""

        mapeamento = {
            "alinhamento": "text-align",
            "text-align": "text-align",
            "tamanho_fonte": "font-size",
            "font-size": "font-size",
            "peso_fonte": "font-weight",
            "font-weight": "font-weight",
            "cor_texto": "color",
            "color": "color",
            "cor_fundo": "background-color",
            "background-color": "background-color",
            "cor_borda": "border-color",
            "border-color": "border-color",
            "largura_borda": "border-width",
            "border-width": "border-width",
            "estilo_borda": "border-style",
            "border-style": "border-style",
            "raio_borda": "border-radius",
            "border-radius": "border-radius",
            "sombra": "box-shadow",
            "box-shadow": "box-shadow",
            "margem_topo": "margin-top",
            "margin-top": "margin-top",
            "margem_baixo": "margin-bottom",
            "margin-bottom": "margin-bottom",
            "padding_topo": "padding-top",
            "padding-top": "padding-top",
            "padding_baixo": "padding-bottom",
            "padding-bottom": "padding-bottom",
            "padding_lateral": "padding-left",  # também aplica em padding-right
            "opacidade": "opacity",
            "opacity": "opacity",
            "largura_maxima": "max-width",
            "max-width": "max-width",
            "gap": "gap",
            "animacao": "animation",
            "animation": "animation",
            "backdrop_filter": "backdrop-filter",
        }

        mapa_sombras = {
            "none": "none",
            "nenhuma": "none",
            "suave": "0 2px 8px -2px rgba(0, 0, 0, 0.08), 0 1px 4px -1px rgba(0, 0, 0, 0.04)",
            "media": "0 6px 16px -4px rgba(0, 0, 0, 0.12), 0 2px 6px -1px rgba(0, 0, 0, 0.06)",
            "forte": "0 12px 28px -6px rgba(0, 0, 0, 0.2), 0 4px 12px -2px rgba(0, 0, 0, 0.1)",
            "glow": "0 0 24px var(--cor-primaria, #2563eb)",
        }

        mapa_animacoes = {
            "fade": "biositeFadeIn 0.4s ease-out forwards",
            "fade-up": "biositeFadeInUp 0.5s cubic-bezier(0.16, 1, 0.3, 1) forwards",
            "scale": "biositeScaleIn 0.35s cubic-bezier(0.16, 1, 0.3, 1) forwards",
            "slide": "biositeSlideIn 0.4s cubic-bezier(0.16, 1, 0.3, 1) forwards",
        }

        def _formatar_valor(chave: str, prop: str, valor: Any) -> str:
            if chave in ["sombra", "box-shadow"]:
                return mapa_sombras.get(str(valor).lower(), str(valor))
            if chave in ["animacao", "animation"]:
                return mapa_animacoes.get(str(valor).lower(), str(valor))
            if chave == "backdrop_filter":
                return f"blur({valor}px)" if isinstance(valor, (int, float)) else str(valor)

            if prop in [
                "font-size",
                "border-width",
                "border-radius",
                "margin-top",
                "margin-bottom",
                "padding-top",
                "padding-bottom",
                "padding-left",
                "padding-right",
                "max-width",
                "gap",
            ]:
                val_str = str(valor).strip()
                return (
                    val_str
                    if "px" in val_str or "%" in val_str or "rem" in val_str or "vw" in val_str
                    else f"{val_str}px"
                )
            return str(valor)

        css_regras = []
        base_regras = []
        base = estilos.get("base", {})
        if isinstance(base, dict):
            for k, v in base.items():
                prop_css = mapeamento.get(k)
                if prop_css and v:
                    val = _formatar_valor(k, prop_css, v)
                    base_regras.append(f"{prop_css}: {val};")
                    if k == "padding_lateral":
                        base_regras.append(f"padding-right: {val};")
                    if (
                        prop_css == "border-width"
                        and "border-style" not in base
                        and "estilo_borda" not in base
                    ):
                        base_regras.append("border-style: solid;")

        if base_regras:
            css_regras.append(f"{seletor} {{ {' '.join(base_regras)} }}")

        # Overrides Desktop (aplica a partir de 768px)
        desktop_regras = []
        desktop = estilos.get("desktop", {})
        if isinstance(desktop, dict):
            for k, v in desktop.items():
                prop_css = mapeamento.get(k)
                if prop_css and v:
                    val = _formatar_valor(k, prop_css, v)
                    desktop_regras.append(f"{prop_css}: {val};")
                    if k == "padding_lateral":
                        desktop_regras.append(f"padding-right: {val};")

        if desktop_regras:
            css_regras.append(
                f"@media (min-width: 768px) {{ {seletor} {{ {' '.join(desktop_regras)} }} }}"
            )

        return "\n".join(css_regras)

    def renderizar_elemento(self, elemento: ElementoSite) -> SafeString:
        """Renderiza um ElementoSite com ou sem invólucros do editor."""
        definicao = RegistroElementos.obter(elemento.tipo)
        html_conteudo = definicao.render(elemento)

        classe_seletor = f"biosite-elem-{elemento.id}"
        estilos_css = self.converter_estilos_para_css(elemento.estilos, f".{classe_seletor}")
        tag_style = format_html("<style>{}</style>", mark_safe(estilos_css)) if estilos_css else ""

        if self.eh_editor:
            return format_html(
                """
                <div class="editor-elemento-wrapper biosite-elemento {}"
                     data-elemento-id="{}"
                     data-tipo="{}"
                     data-ordem="{}">
                    <div class="editor-elemento-toolbar">
                        <span class="editor-elemento-badge">{}</span>
                        <div class="editor-elemento-acoes">
                            <button type="button" class="btn-acao-elem" data-acao="duplicar" title="Duplicar">⎘</button>
                            <button type="button" class="btn-acao-elem btn-danger" data-acao="excluir" title="Excluir">✕</button>
                        </div>
                    </div>
                    <div class="editor-elemento-conteudo">
                        {}{}
                    </div>
                </div>
                """,
                classe_seletor,
                elemento.id,
                elemento.tipo,
                elemento.ordem,
                definicao.nome,
                mark_safe(tag_style),
                mark_safe(html_conteudo),
            )

        return format_html(
            '<div class="biosite-elemento biosite-elem-tipo-{} {}">{}{}</div>',
            elemento.tipo.lower(),
            classe_seletor,
            mark_safe(tag_style),
            mark_safe(html_conteudo),
        )

    def renderizar_container(self, container: ContainerSite) -> SafeString:
        """Renderiza recursivamente um ContainerSite e seus elementos/filhos."""
        elementos_html = [
            self.renderizar_elemento(elem)
            for elem in container.elementos.filter(ativo=True).order_by("ordem")
        ]

        filhos_html = [
            self.renderizar_container(filho)
            for filho in container.filhos.filter(ativo=True).order_by("ordem")
        ]

        classe_layout = f"biosite-layout-{container.tipo_layout.lower()}"
        classe_seletor = f"biosite-cont-{container.id}"
        estilos_css = self.converter_estilos_para_css(container.estilos, f".{classe_seletor}")
        tag_style = format_html("<style>{}</style>", mark_safe(estilos_css)) if estilos_css else ""

        if self.eh_editor:
            conteudo_interno = mark_safe("".join(elementos_html) + "".join(filhos_html))
            vazio_aviso = (
                mark_safe(
                    '<div class="editor-container-vazio">Arraste ou clique em um elemento da esquerda para inserir aqui</div>'
                )
                if not elementos_html and not filhos_html
                else ""
            )

            return format_html(
                """
                <div class="editor-container-wrapper biosite-container {} {}"
                     data-container-id="{}"
                     data-layout="{}"
                     data-ordem="{}">
                    <div class="editor-container-header">
                        <span class="editor-container-tag">CONTAINER [{}]</span>
                        <div class="editor-container-acoes">
                            <button type="button" class="btn-acao-container" data-acao="adicionar-elemento">+ Inserir</button>
                        </div>
                    </div>
                    {}{}
                    <div class="editor-container-dropzone sortable-container-elementos" data-container-id="{}">
                        {}
                    </div>
                </div>
                """,
                classe_layout,
                classe_seletor,
                container.id,
                container.tipo_layout,
                container.ordem,
                container.tipo_layout,
                mark_safe(tag_style),
                vazio_aviso,
                container.id,
                conteudo_interno,
            )

        return format_html(
            '<div class="biosite-container {} {}">{}{}{}</div>',
            classe_layout,
            classe_seletor,
            mark_safe(tag_style),
            mark_safe("".join(elementos_html)),
            mark_safe("".join(filhos_html)),
        )

    def renderizar_secao(self, secao: SecaoSite) -> SafeString:
        """Renderiza uma SecaoSite e seus containers raiz."""
        containers_html = [
            self.renderizar_container(c)
            for c in secao.containers.filter(parent__isnull=True, ativo=True).order_by("ordem")
        ]

        classe_seletor = f"biosite-sec-{secao.id}"
        classe_tipo = f"biosite-secao-{secao.tipo.lower()}"
        estilos_css = self.converter_estilos_para_css(secao.estilos, f".{classe_seletor}")
        tag_style = format_html("<style>{}</style>", mark_safe(estilos_css)) if estilos_css else ""

        if self.eh_editor:
            return format_html(
                """
                <div class="editor-secao-divider" data-ordem="{}">
                    <button type="button" class="btn-add-secao-inline" data-ordem-depois="{}">
                        + Nova Seção
                    </button>
                </div>
                <section class="editor-secao-wrapper biosite-secao {} {}"
                         data-secao-id="{}"
                         data-ordem="{}"
                         data-tipo="{}">
                    <div class="editor-secao-header">
                        <div class="editor-secao-titulo">
                            <span class="editor-secao-drag-handle" title="Arraste para reordenar seções">⋮⋮</span>
                            <span class="editor-secao-nome">{}</span>
                            <span class="editor-secao-tipo">({})</span>
                        </div>
                        <div class="editor-secao-acoes">
                            <button type="button" class="btn-acao-secao" data-acao="salvar-bloco" title="Salvar seção como Bloco Reutilizável">💾</button>
                            <button type="button" class="btn-acao-secao" data-acao="duplicar" title="Duplicar seção">⎘</button>
                            <button type="button" class="btn-acao-secao btn-danger" data-acao="excluir" title="Excluir seção">✕</button>
                        </div>
                    </div>
                    {}{}
                </section>
                """,
                secao.ordem,
                secao.ordem,
                classe_tipo,
                classe_seletor,
                secao.id,
                secao.ordem,
                secao.tipo,
                escape(secao.nome_interno),
                secao.tipo,
                mark_safe(tag_style),
                mark_safe("".join(containers_html)),
            )

        return format_html(
            '<section class="biosite-secao {} {}">{}{}</section>',
            classe_tipo,
            classe_seletor,
            mark_safe(tag_style),
            mark_safe("".join(containers_html)),
        )

    def renderizar_pagina(self, pagina: PaginaSite) -> SafeString:
        """Renderiza a página completa com todas as suas seções ordenadas e tokens do Design System."""
        from .models import garantir_configuracao_visual

        config_visual = getattr(pagina.projeto, "configuracao_visual", None)
        if not config_visual:
            config_visual = garantir_configuracao_visual(pagina.projeto)

        bloco_tokens = config_visual.gerar_bloco_css()
        tag_tokens = format_html(
            '<style id="biosite-tokens-css">{}</style>', mark_safe(bloco_tokens)
        )

        secoes = pagina.secoes.filter(ativa=True).order_by("ordem")
        secoes_html = [self.renderizar_secao(s) for s in secoes]

        if self.eh_editor:
            add_fim = format_html(
                """
                <div class="editor-secao-divider final-divider">
                    <button type="button" class="btn-add-secao-inline" data-ordem-depois="999999">
                        + Adicionar Nova Seção
                    </button>
                </div>
                """
            )
            vazio_html = (
                mark_safe(
                    """
                    <div class="editor-pagina-vazia">
                        <div class="vazio-icone">📱</div>
                        <h3>Sua página está pronta para receber conteúdo</h3>
                        <p>Clique no botão abaixo para adicionar sua primeira seção.</p>
                        <button type="button" class="btn btn-primary btn-add-secao-inline" data-ordem-depois="0">
                            + Adicionar Primeira Seção
                        </button>
                    </div>
                    """
                )
                if not secoes_html
                else ""
            )

            return format_html(
                """
                <div class="biosite-canvas-root editor-mode" id="biosite-canvas-root" data-pagina-id="{}">
                    {}
                    <div id="editor-secoes-container" class="sortable-secoes">
                        {}{}
                    </div>
                    {}
                </div>
                """,
                pagina.id,
                tag_tokens,
                vazio_html,
                mark_safe("".join(secoes_html)),
                add_fim if secoes_html else "",
            )

        return format_html(
            """
            <div class="biosite-canvas-root preview-mode" id="biosite-canvas-root" data-pagina-id="{}">
                {}
                {}
            </div>
            """,
            pagina.id,
            tag_tokens,
            mark_safe("".join(secoes_html)),
        )

    def renderizar_snapshot(self, snapshot: dict[str, Any]) -> SafeString:
        """Renderiza um snapshot estrutural de TemplateSite em memória (Preview Fiel)."""
        config_dict = snapshot.get("configuracao_visual", {})
        bloco_tokens = gerar_bloco_tokens_de_dict(config_dict)
        tag_tokens = format_html(
            '<style id="biosite-tokens-css">{}</style>', mark_safe(bloco_tokens)
        )

        paginas = snapshot.get("paginas", [])
        secoes_html = []
        if paginas:
            primeira_pagina = paginas[0]
            for idx_s, s_dict in enumerate(primeira_pagina.get("secoes", [])):
                secoes_html.append(self.renderizar_snapshot_secao(s_dict, id_secao=idx_s + 1))

        return format_html(
            """
            <div class="biosite-canvas-root preview-mode" id="biosite-canvas-root" data-pagina-id="snapshot">
                {}
                {}
            </div>
            """,
            tag_tokens,
            mark_safe("".join(secoes_html)),
        )

    def renderizar_snapshot_secao(
        self, secao_dict: dict[str, Any], id_secao: int = 1
    ) -> SafeString:
        """Renderiza uma seção de snapshot estrutural em memória."""
        classe_seletor = f"biosite-sec-snap-{id_secao}"
        classe_tipo = f"biosite-secao-{secao_dict.get('tipo', 'normal').lower()}"
        estilos_css = self.converter_estilos_para_css(
            secao_dict.get("estilos", {}), f".{classe_seletor}"
        )
        tag_style = format_html("<style>{}</style>", mark_safe(estilos_css)) if estilos_css else ""

        containers_html = []
        for idx_c, c_dict in enumerate(secao_dict.get("containers", [])):
            containers_html.append(
                self._renderizar_snapshot_container(c_dict, id_container=f"{id_secao}_{idx_c + 1}")
            )

        return format_html(
            '<section class="biosite-secao {} {}">{}{}</section>',
            classe_tipo,
            classe_seletor,
            mark_safe(tag_style),
            mark_safe("".join(containers_html)),
        )

    def _renderizar_snapshot_container(
        self, container_dict: dict[str, Any], id_container: str = "1"
    ) -> SafeString:
        tipo_layout = container_dict.get("tipo_layout", "stack")
        classe_layout = f"layout-{tipo_layout}"
        classe_seletor = f"biosite-cont-snap-{id_container}"
        estilos_css = self.converter_estilos_para_css(
            container_dict.get("estilos", {}), f".{classe_seletor}"
        )
        tag_style = format_html("<style>{}</style>", mark_safe(estilos_css)) if estilos_css else ""

        elementos_html = []
        for idx_e, e_dict in enumerate(container_dict.get("elementos", [])):
            tipo = e_dict.get("tipo", "").lower()
            if RegistroElementos.eh_valido(tipo):
                definicao = RegistroElementos.obter(tipo)
                conteudo = copy.deepcopy(definicao.conteudo_padrao())
                conteudo.update(e_dict.get("conteudo", {}))
                elem_fake = type(
                    "ElementoSnapshot",
                    (),
                    {
                        "id": f"{id_container}_{idx_e + 1}",
                        "tipo": tipo.upper(),
                        "conteudo": conteudo,
                        "estilos": e_dict.get("estilos", {}),
                    },
                )()
                elem_html = definicao.render(elem_fake)
                elem_classe = f"biosite-elem-snap-{elem_fake.id}"
                elem_css = self.converter_estilos_para_css(elem_fake.estilos, f".{elem_classe}")
                elem_style = (
                    format_html("<style>{}</style>", mark_safe(elem_css)) if elem_css else ""
                )
                elementos_html.append(
                    format_html(
                        '<div class="biosite-elemento {}">{}{}</div>',
                        elem_classe,
                        mark_safe(elem_style),
                        mark_safe(elem_html),
                    )
                )

        filhos_html = []
        for idx_f, f_dict in enumerate(container_dict.get("filhos", [])):
            filhos_html.append(
                self._renderizar_snapshot_container(
                    f_dict, id_container=f"{id_container}_f{idx_f + 1}"
                )
            )

        return format_html(
            '<div class="biosite-container {} {}">{}{}{}</div>',
            classe_layout,
            classe_seletor,
            mark_safe(tag_style),
            mark_safe("".join(elementos_html)),
            mark_safe("".join(filhos_html)),
        )


def gerar_bloco_tokens_de_dict(config_dict: dict[str, Any]) -> str:
    """Gera bloco CSS :root com variáveis a partir de um dicionário de configuração visual."""
    tokens = {
        "--cor-primaria": config_dict.get("cor_primaria", "#2563eb"),
        "--cor-secundaria": config_dict.get("cor_secundaria", "#38bdf8"),
        "--cor-fundo": config_dict.get("cor_fundo", "#ffffff"),
        "--cor-superficie": config_dict.get("cor_superficie", "#f8fafc"),
        "--cor-texto": config_dict.get("cor_texto", "#0f172a"),
        "--cor-texto-secundario": config_dict.get("cor_texto_secundario", "#64748b"),
        "--fonte-principal": config_dict.get("fonte_principal", "Inter, sans-serif"),
        "--fonte-titulos": config_dict.get("fonte_titulos", "Inter, sans-serif"),
        "--radius-padrao": config_dict.get("radius_padrao", "12px"),
        "--sombra-padrao": config_dict.get("sombra_padrao", "suave"),
        "--largura-maxima-mobile": f"{config_dict.get('largura_maxima_mobile', 390)}px",
    }
    regras = [f"  {k}: {v};" for k, v in tokens.items()]
    return ":root, .biosite-canvas-root {\n" + "\n".join(regras) + "\n}"


def renderizar_pagina(pagina: PaginaSite, modo_editor: bool = False) -> SafeString:
    """Função utilitária para renderizar uma página completa."""
    modo = "editor" if modo_editor else "preview"
    return RenderizadorBioSite(modo=modo).renderizar_pagina(pagina)
