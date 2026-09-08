/**
 * propriedades.js — Painel Lateral Contextual de Propriedades e Estilos Mobile-First (Prompt 6)
 */

export class PropriedadesManager {
    constructor(editor) {
        this.editor = editor;
        this.painelEl = document.getElementById('studio-sidebar-right');
        this.conteudoEl = document.getElementById('propriedades-conteudo');
        this.itemAtual = null;
        this.escopoAtivo = 'base'; // 'base' (mobile) ou 'desktop'
    }

    limpar() {
        this.itemAtual = null;
        if (this.conteudoEl) {
            this.conteudoEl.innerHTML = `
                <div class="propriedades-vazio">
                    <p>Selecione um elemento, seção ou container no canvas para editar suas propriedades.</p>
                </div>
            `;
        }
    }

    carregarPropriedades(tipo, id, el) {
        this.itemAtual = { tipo, id, el };
        if (!this.conteudoEl) return;

        if (tipo === 'elemento') {
            this.renderizarPropriedadesElemento(id, el);
        } else if (tipo === 'secao') {
            this.renderizarPropriedadesSecao(id, el);
        } else if (tipo === 'container') {
            this.renderizarPropriedadesContainer(id, el);
        }
    }

    renderizarPropriedadesElemento(id, el) {
        const tipoElem = (el.dataset.tipo || '').toUpperCase();
        const textoAtual = el.querySelector('.elemento-titulo, .elemento-texto, .elemento-botao span, .servico-titulo')?.innerText || '';
        const linkEl = el.querySelector('a');
        const urlAtual = linkEl ? linkEl.getAttribute('href') || '' : '';

        let camposEspecificosHtml = '';

        if (tipoElem === 'TITULO') {
            camposEspecificosHtml = `
                <div class="form-group-prop">
                    <label class="prop-label">Texto do Título</label>
                    <input type="text" class="prop-input" id="prop-campo-texto" value="${this.escapeHtml(textoAtual)}">
                </div>
                <div class="form-group-prop">
                    <label class="prop-label">Nível Hierárquico</label>
                    <select class="prop-select" id="prop-campo-nivel">
                        <option value="h1">H1 — Título Principal</option>
                        <option value="h2" selected>H2 — Subtítulo</option>
                        <option value="h3">H3 — Seção</option>
                        <option value="h4">H4 — Bloco</option>
                    </select>
                </div>
            `;
        } else if (tipoElem === 'TEXTO') {
            camposEspecificosHtml = `
                <div class="form-group-prop">
                    <label class="prop-label">Texto do Parágrafo</label>
                    <textarea class="prop-input" id="prop-campo-texto" rows="4">${this.escapeHtml(textoAtual)}</textarea>
                </div>
            `;
        } else if (tipoElem === 'BOTAO') {
            camposEspecificosHtml = `
                <div class="form-group-prop">
                    <label class="prop-label">Texto do Botão</label>
                    <input type="text" class="prop-input" id="prop-campo-texto" value="${this.escapeHtml(textoAtual)}">
                </div>
                <div class="form-group-prop">
                    <label class="prop-label">Link de Destino (URL)</label>
                    <input type="text" class="prop-input" id="prop-campo-url" value="${this.escapeHtml(urlAtual)}" placeholder="https://, tel:, mailto:">
                </div>
                <div class="form-group-prop">
                    <label class="prop-label">Estilo do Botão</label>
                    <select class="prop-select" id="prop-campo-estilo_visual">
                        <option value="solido">Sólido (Cor Primária)</option>
                        <option value="outline">Contorno (Outline)</option>
                        <option value="ghost">Transparente (Ghost)</option>
                        <option value="glass">Vidro (Glassmorphism)</option>
                    </select>
                </div>
                <div class="form-group-prop">
                    <label class="prop-label">
                        <input type="checkbox" id="prop-campo-largura_total" checked> Largura Total (Mobile-First)
                    </label>
                </div>
            `;
        } else if (tipoElem === 'WHATSAPP') {
            camposEspecificosHtml = `
                <div class="form-group-prop">
                    <label class="prop-label">Número (com DDD)</label>
                    <input type="text" class="prop-input" id="prop-campo-numero" value="5511999999999" placeholder="Ex: 5511999999999">
                </div>
                <div class="form-group-prop">
                    <label class="prop-label">Texto do Botão</label>
                    <input type="text" class="prop-input" id="prop-campo-texto" value="${this.escapeHtml(textoAtual || 'Falar no WhatsApp')}">
                </div>
                <div class="form-group-prop">
                    <label class="prop-label">Mensagem Pré-definida</label>
                    <input type="text" class="prop-input" id="prop-campo-mensagem" value="Olá! Gostaria de mais informações.">
                </div>
                <div class="form-group-prop">
                    <label class="prop-label">Tipo de Exibição</label>
                    <select class="prop-select" id="prop-campo-estilo_botao">
                        <option value="solido">Botão Normal na Página</option>
                        <option value="flutuante">Botão Flutuante Fixo (Canto)</option>
                    </select>
                </div>
            `;
        } else if (tipoElem === 'TELEFONE') {
            camposEspecificosHtml = `
                <div class="form-group-prop">
                    <label class="prop-label">Número de Telefone</label>
                    <input type="text" class="prop-input" id="prop-campo-numero" value="(11) 99999-9999">
                </div>
                <div class="form-group-prop">
                    <label class="prop-label">Texto do Botão</label>
                    <input type="text" class="prop-input" id="prop-campo-texto" value="${this.escapeHtml(textoAtual || 'Ligar Agora')}">
                </div>
            `;
        } else if (tipoElem === 'EMAIL') {
            camposEspecificosHtml = `
                <div class="form-group-prop">
                    <label class="prop-label">Endereço de E-mail</label>
                    <input type="email" class="prop-input" id="prop-campo-email" value="contato@meubiosite.com">
                </div>
                <div class="form-group-prop">
                    <label class="prop-label">Texto do Botão</label>
                    <input type="text" class="prop-input" id="prop-campo-texto" value="${this.escapeHtml(textoAtual || 'Enviar E-mail')}">
                </div>
                <div class="form-group-prop">
                    <label class="prop-label">Assunto Opcional</label>
                    <input type="text" class="prop-input" id="prop-campo-assunto" value="Contato via BioSite">
                </div>
            `;
        } else if (tipoElem === 'WEBSITE') {
            camposEspecificosHtml = `
                <div class="form-group-prop">
                    <label class="prop-label">URL do Site</label>
                    <input type="url" class="prop-input" id="prop-campo-url" value="${this.escapeHtml(urlAtual || 'https://')}">
                </div>
                <div class="form-group-prop">
                    <label class="prop-label">Texto do Botão</label>
                    <input type="text" class="prop-input" id="prop-campo-texto" value="${this.escapeHtml(textoAtual || 'Acessar Site')}">
                </div>
            `;
        } else if (tipoElem === 'REDES_SOCIAIS') {
            camposEspecificosHtml = `
                <div class="form-group-prop">
                    <label class="prop-label">Formato de Exibição</label>
                    <select class="prop-select" id="prop-campo-formato">
                        <option value="icones">Apenas Ícones</option>
                        <option value="botoes">Botões com Texto</option>
                    </select>
                </div>
                <div class="form-group-prop">
                    <label class="prop-label">Instagram URL</label>
                    <input type="url" class="prop-input prop-social-link" data-rede="instagram" value="https://instagram.com/">
                </div>
                <div class="form-group-prop">
                    <label class="prop-label">WhatsApp URL</label>
                    <input type="url" class="prop-input prop-social-link" data-rede="whatsapp" value="https://wa.me/5511999999999">
                </div>
                <div class="form-group-prop">
                    <label class="prop-label">LinkedIn URL</label>
                    <input type="url" class="prop-input prop-social-link" data-rede="linkedin" value="https://linkedin.com/">
                </div>
                <div class="form-group-prop">
                    <label class="prop-label">YouTube URL</label>
                    <input type="url" class="prop-input prop-social-link" data-rede="youtube" value="https://youtube.com/">
                </div>
            `;
        } else if (tipoElem === 'AGENDAMENTO_EXTERNO') {
            camposEspecificosHtml = `
                <div class="form-group-prop">
                    <label class="prop-label">Texto do Botão</label>
                    <input type="text" class="prop-input" id="prop-campo-texto" value="${this.escapeHtml(textoAtual || '📅 Agendar Atendimento')}">
                </div>
                <div class="form-group-prop">
                    <label class="prop-label">URL do Google Calendar / Agendamento</label>
                    <input type="url" class="prop-input" id="prop-campo-url" value="${this.escapeHtml(urlAtual || 'https://calendar.google.com/')}" placeholder="https://calendar.google.com/...">
                    <span style="font-size: 0.65rem; color: var(--studio-text-muted);">Link externo seguro para seu calendário</span>
                </div>
            `;
        } else if (tipoElem === 'MAPA') {
            camposEspecificosHtml = `
                <div class="form-group-prop">
                    <label class="prop-label">Endereço Completo</label>
                    <input type="text" class="prop-input" id="prop-campo-endereco" value="Av. Paulista, 1000 - São Paulo, SP">
                </div>
                <div class="form-group-prop">
                    <label class="prop-label">Texto do Botão</label>
                    <input type="text" class="prop-input" id="prop-campo-texto" value="${this.escapeHtml(textoAtual || '📍 Ver no Google Maps')}">
                </div>
                <div class="form-group-prop">
                    <label class="prop-label">Link Personalizado (Opcional)</label>
                    <input type="url" class="prop-input" id="prop-campo-url_personalizada" placeholder="https://maps.google.com/...">
                </div>
            `;
        } else if (tipoElem === 'AVATAR') {
            camposEspecificosHtml = `
                <div class="form-group-prop">
                    <label class="prop-label">URL da Imagem de Perfil</label>
                    <input type="url" class="prop-input" id="prop-campo-url" placeholder="https://...">
                    <button type="button" class="btn-upload-midia" style="margin-top: 0.35rem;" id="btn-abrir-midia">📁 Escolher da Galeria de Mídias</button>
                </div>
                <div class="form-group-prop">
                    <label class="prop-label">Forma do Avatar</label>
                    <select class="prop-select" id="prop-campo-forma">
                        <option value="circulo">Circular (50%)</option>
                        <option value="arredondado">Arredondado Suave</option>
                        <option value="quadrado">Quadrado</option>
                    </select>
                </div>
                <div class="form-group-prop">
                    <label class="prop-label">Tamanho (px)</label>
                    <input type="range" class="prop-input" id="prop-campo-tamanho" min="48" max="180" value="100" oninput="document.getElementById('val-tamanho-avatar').textContent = this.value + 'px'">
                    <span id="val-tamanho-avatar" style="font-size: 0.75rem; color: var(--studio-text-muted);">100px</span>
                </div>
            `;
        } else if (tipoElem === 'DIVISOR') {
            camposEspecificosHtml = `
                <div class="form-group-prop">
                    <label class="prop-label">Estilo da Linha</label>
                    <select class="prop-select" id="prop-campo-estilo">
                        <option value="solid">Sólida Contínua</option>
                        <option value="dashed">Tracejada (Dashed)</option>
                        <option value="dotted">Pontilhada (Dotted)</option>
                    </select>
                </div>
                <div class="form-group-prop">
                    <label class="prop-label">Largura</label>
                    <select class="prop-select" id="prop-campo-largura">
                        <option value="100%">100% (Largura Total)</option>
                        <option value="75%">75%</option>
                        <option value="50%">50%</option>
                        <option value="25%">25%</option>
                    </select>
                </div>
                <div class="form-group-prop">
                    <label class="prop-label">Espessura (px)</label>
                    <input type="number" class="prop-input" id="prop-campo-espessura" value="1" min="1" max="6">
                </div>
            `;
        } else if (tipoElem === 'IMAGEM') {
            camposEspecificosHtml = `
                <div class="form-group-prop">
                    <label class="prop-label">URL da Imagem</label>
                    <input type="url" class="prop-input" id="prop-campo-url" placeholder="https://...">
                    <button type="button" class="btn-upload-midia" style="margin-top: 0.35rem;" id="btn-abrir-midia">📁 Escolher da Galeria de Mídias</button>
                </div>
                <div class="form-group-prop">
                    <label class="prop-label">Texto Alternativo (Alt)</label>
                    <input type="text" class="prop-input" id="prop-campo-alt_text" placeholder="Descreva a imagem">
                </div>
                <div class="form-group-prop">
                    <label class="prop-label">Ajuste (Fit)</label>
                    <select class="prop-select" id="prop-campo-fit">
                        <option value="cover">Preencher e Cortar (Cover)</option>
                        <option value="contain">Conter Completa (Contain)</option>
                    </select>
                </div>
            `;
        } else if (tipoElem === 'ESPACADOR') {
            camposEspecificosHtml = `
                <div class="form-group-prop">
                    <label class="prop-label">Altura do Espaçador (px)</label>
                    <input type="range" class="prop-input" id="prop-campo-altura" min="8" max="120" value="24" oninput="document.getElementById('val-altura').textContent = this.value + 'px'">
                    <span id="val-altura" style="font-size: 0.75rem; color: var(--studio-text-muted);">24px</span>
                </div>
            `;
        } else if (tipoElem === 'VIDEO') {
            const urlVideo = el.querySelector('iframe, video')?.getAttribute('src') || '';
            camposEspecificosHtml = `
                <div class="form-group-prop">
                    <label class="prop-label">URL do Vídeo (YouTube, Vimeo, MP4)</label>
                    <input type="url" class="prop-input" id="prop-campo-url" value="${this.escapeHtml(urlVideo)}" placeholder="https://youtube.com/watch?v=...">
                </div>
                <div class="form-group-prop">
                    <label class="prop-label">Raio da Borda (px)</label>
                    <input type="number" class="prop-input" id="prop-campo-raio_borda" value="8" min="0" max="40">
                </div>
            `;
        } else if (tipoElem === 'FORMA') {
            camposEspecificosHtml = `
                <div class="form-group-prop">
                    <label class="prop-label">Tipo de Forma</label>
                    <select class="prop-select" id="prop-campo-subtipo">
                        <option value="retangulo">Retângulo / Bloco</option>
                        <option value="circulo">Círculo</option>
                    </select>
                </div>
                <div class="form-group-prop">
                    <label class="prop-label">Cor de Preenchimento</label>
                    <input type="color" class="prop-input" id="prop-campo-cor_fundo" value="#38bdf8" style="height: 36px;">
                </div>
                <div class="form-group-prop">
                    <label class="prop-label">Opacidade</label>
                    <input type="range" class="prop-input" id="prop-campo-opacidade" min="0.1" max="1" step="0.05" value="1">
                </div>
            `;
        } else if (tipoElem === 'HTML_EMBED') {
            camposEspecificosHtml = `
                <div class="form-group-prop">
                    <label class="prop-label">Código HTML (Sandbox)</label>
                    <textarea class="prop-input" id="prop-campo-codigo_html" rows="5" style="font-family: monospace; font-size: 0.75rem;"></textarea>
                </div>
                <div class="form-group-prop">
                    <label class="prop-label">Altura (px)</label>
                    <input type="number" class="prop-input" id="prop-campo-altura_px" value="120" min="40" max="1200">
                </div>
            `;
        } else if (tipoElem === 'LOGO') {
            camposEspecificosHtml = `
                <div class="form-group-prop">
                    <label class="prop-label">URL da Imagem do Logo</label>
                    <input type="url" class="prop-input" id="prop-campo-url_imagem" placeholder="https://...">
                    <button type="button" class="btn-upload-midia" style="margin-top: 0.35rem;" id="btn-abrir-midia">📁 Escolher da Galeria de Mídias</button>
                </div>
                <div class="form-group-prop">
                    <label class="prop-label">Nome da Marca</label>
                    <input type="text" class="prop-input" id="prop-campo-texto_alternativo" value="Logo">
                </div>
                <div class="form-group-prop">
                    <label class="prop-label">Largura (px)</label>
                    <input type="number" class="prop-input" id="prop-campo-largura_px" value="140" min="40" max="400">
                </div>
                <div class="form-group-prop">
                    <label class="prop-label">Link no Logo (URL)</label>
                    <input type="url" class="prop-input" id="prop-campo-link_url" placeholder="https://...">
                </div>
            `;
        }

        const xVal = parseFloat(el.dataset.xPct || 10).toFixed(1);
        const yVal = parseFloat(el.dataset.yPx || 20).toFixed(0);
        const wVal = parseFloat(el.dataset.wPct || 80).toFixed(0);
        const zVal = el.style.zIndex || el.dataset.zIndex || 1;

        this.conteudoEl.innerHTML = `
            <div class="propriedades-header">
                <span class="propriedades-titulo">Elemento: ${tipoElem}</span>
                <span style="font-size: 0.75rem; color: var(--studio-accent);">#${id}</span>
            </div>

            <div class="propriedades-form">
                <!-- Seletor de Escopo: Mobile / Desktop -->
                <div class="prop-btn-group" style="margin-bottom: 0.5rem;">
                    <button type="button" class="${this.escopoAtivo === 'base' ? 'active' : ''}" id="btn-escopo-mobile">📱 Mobile (Base)</button>
                    <button type="button" class="${this.escopoAtivo === 'desktop' ? 'active' : ''}" id="btn-escopo-desktop">💻 Desktop</button>
                </div>

                <!-- Campos Específicos do Tipo -->
                ${camposEspecificosHtml}

                <!-- Posicionamento Livre no Canvas & Camadas (Canva / Paint) -->
                <div style="margin-top: 1rem; padding-top: 1rem; border-top: 1px solid var(--studio-border);">
                    <span class="prop-label" style="font-weight: 700; color: var(--studio-accent); margin-bottom: 0.5rem; display: block;">Posição & Camadas (Canvas Livre)</span>

                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem; margin-bottom: 0.5rem;">
                        <div class="form-group-prop" style="margin-bottom: 0;">
                            <label class="prop-label" style="font-size: 0.7rem;">X (% Canvas)</label>
                            <input type="number" class="prop-input" id="prop-pos-x" step="0.5" min="0" max="100" value="${xVal}">
                        </div>
                        <div class="form-group-prop" style="margin-bottom: 0;">
                            <label class="prop-label" style="font-size: 0.7rem;">Y (px Topo)</label>
                            <input type="number" class="prop-input" id="prop-pos-y" step="5" min="0" value="${yVal}">
                        </div>
                    </div>

                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem; margin-bottom: 0.5rem;">
                        <div class="form-group-prop" style="margin-bottom: 0;">
                            <label class="prop-label" style="font-size: 0.7rem;">Largura (%)</label>
                            <input type="number" class="prop-input" id="prop-pos-w" step="1" min="10" max="100" value="${wVal}">
                        </div>
                        <div class="form-group-prop" style="margin-bottom: 0;">
                            <label class="prop-label" style="font-size: 0.7rem;">Camada (Z-Index)</label>
                            <input type="number" class="prop-input" id="prop-pos-z" min="1" max="999" value="${zVal}">
                        </div>
                    </div>

                    <div style="display: flex; gap: 4px; margin-top: 0.5rem; flex-wrap: wrap;">
                        <button type="button" class="btn-studio-tool" id="btn-prop-z-avancar" title="Avançar uma camada">↑ Avançar</button>
                        <button type="button" class="btn-studio-tool" id="btn-prop-z-recuar" title="Recuar uma camada">↓ Recuar</button>
                        <button type="button" class="btn-studio-tool" id="btn-prop-z-frente" title="Trazer para frente">⤒ Frente</button>
                        <button type="button" class="btn-studio-tool" id="btn-prop-z-fundo" title="Enviar para o fundo">⤓ Fundo</button>
                    </div>
                </div>

                <!-- Estilos Globais vs Locais -->
                <div style="margin-top: 1rem; padding-top: 1rem; border-top: 1px solid var(--studio-border);">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem;">
                        <span class="prop-label" style="margin: 0;">Estilos & Efeitos</span>
                        <button type="button" id="btn-reset-estilos" style="background: none; border: none; font-size: 0.7rem; color: var(--studio-accent); cursor: pointer;" title="Remove overrides locais e restaura valores do Design System">
                            ↺ Usar padrão do projeto
                        </button>
                    </div>

                    <div class="form-group-prop">
                        <label class="prop-label">Cor de Fundo</label>
                        <input type="color" class="prop-input" id="prop-estilo-cor_fundo" style="height: 36px; padding: 2px;">
                    </div>
                    <div class="form-group-prop">
                        <label class="prop-label">Cor do Texto</label>
                        <input type="color" class="prop-input" id="prop-estilo-cor_texto" style="height: 36px; padding: 2px;">
                    </div>
                    <div class="form-group-prop">
                        <label class="prop-label">Sombra</label>
                        <select class="prop-select" id="prop-estilo-sombra">
                            <option value="none">Nenhuma</option>
                            <option value="suave">Suave</option>
                            <option value="media">Média</option>
                            <option value="forte">Forte</option>
                            <option value="glow">Glow Iluminado</option>
                        </select>
                    </div>
                    <div class="form-group-prop">
                        <label class="prop-label">Animação de Entrada</label>
                        <select class="prop-select" id="prop-estilo-animacao">
                            <option value="none">Nenhuma</option>
                            <option value="fade">Fade (Suave)</option>
                            <option value="fade-up">Fade Up (Subida)</option>
                            <option value="scale">Zoom / Scale</option>
                            <option value="slide">Slide Lateral</option>
                        </select>
                    </div>
                </div>

                <!-- Ações -->
                <div style="margin-top: 1rem; padding-top: 1rem; border-top: 1px solid var(--studio-border); display: flex; justify-content: space-between;">
                    <button type="button" class="btn-acao-elem" id="btn-prop-duplicar">⎘ Duplicar</button>
                    <button type="button" class="btn-acao-elem btn-danger" id="btn-prop-excluir">✕ Excluir</button>
                </div>
            </div>
        `;

        this.vincularEventosElemento(id, el, tipoElem);
    }

    vincularEventosElemento(id, el, tipoElem) {
        document.getElementById('btn-escopo-mobile')?.addEventListener('click', () => {
            this.escopoAtivo = 'base';
            this.renderizarPropriedadesElemento(id, el);
        });
        document.getElementById('btn-escopo-desktop')?.addEventListener('click', () => {
            this.escopoAtivo = 'desktop';
            this.renderizarPropriedadesElemento(id, el);
        });

        // Reset de override para usar tokens do Design System
        document.getElementById('btn-reset-estilos')?.addEventListener('click', () => {
            const estilos = {};
            estilos[this.escopoAtivo] = {
                cor_fundo: '',
                cor_texto: '',
                sombra: 'none',
                animacao: 'none',
            };
            el.style.backgroundColor = '';
            el.style.color = '';
            el.style.boxShadow = '';
            el.style.animation = '';

            this.editor.autosaveManager.agendarSalvamento({
                elemento_id: id,
                estilos: estilos,
            });
        });

        // Sincronização genérica de campos de conteúdo
        const camposConteudo = [
            'texto', 'url', 'numero', 'mensagem', 'email', 'assunto',
            'endereco', 'url_personalizada', 'forma', 'tamanho', 'altura',
            'estilo', 'largura', 'espessura', 'fit', 'alt_text', 'estilo_visual',
            'estilo_botao', 'formato', 'subtipo', 'cor_fundo', 'opacidade',
            'raio_borda', 'codigo_html', 'altura_px', 'url_imagem',
            'texto_alternativo', 'largura_px', 'link_url'
        ];

        camposConteudo.forEach(campoNome => {
            const input = document.getElementById(`prop-campo-${campoNome}`);
            if (input) {
                const evento = (input.tagName === 'INPUT' && input.type === 'text') ? 'input' : 'change';
                input.addEventListener(evento, (e) => {
                    const valor = input.type === 'checkbox' ? input.checked : e.target.value;
                    const conteudo = {};
                    conteudo[campoNome] = valor;

                    // Atualização instantânea no DOM se aplicável
                    if (campoNome === 'texto') {
                        const alvo = el.querySelector('.elemento-titulo, .elemento-texto, .elemento-botao span');
                        if (alvo) alvo.innerText = valor;
                    }

                    this.editor.autosaveManager.agendarSalvamento({
                        elemento_id: id,
                        conteudo: conteudo,
                    });
                });
            }
        });

        // Posição no Canvas Livre (X, Y, W, Z)
        const inputPosX = document.getElementById('prop-pos-x');
        const inputPosY = document.getElementById('prop-pos-y');
        const inputPosW = document.getElementById('prop-pos-w');
        const inputPosZ = document.getElementById('prop-pos-z');

        const atualizarPosicao = () => {
            const x = parseFloat(inputPosX?.value || el.dataset.xPct || 0);
            const y = parseFloat(inputPosY?.value || el.dataset.yPx || 0);
            const w = parseFloat(inputPosW?.value || el.dataset.wPct || 80);
            const z = parseInt(inputPosZ?.value || el.style.zIndex || 1, 10);

            el.style.left = `${x}%`;
            el.style.top = `${y}px`;
            el.style.width = `${w}%`;
            el.style.zIndex = z;

            el.dataset.xPct = x;
            el.dataset.yPx = y;
            el.dataset.wPct = w;
            el.dataset.zIndex = z;

            if (this.editor.canvasLivreManager) {
                this.editor.canvasLivreManager._persistirPosicao(id, {
                    x_pct: x,
                    y_px: y,
                    w_pct: w,
                    z_index: z,
                    h_auto: el.dataset.hAuto !== 'false'
                });
            }
        };

        inputPosX?.addEventListener('change', atualizarPosicao);
        inputPosY?.addEventListener('change', atualizarPosicao);
        inputPosW?.addEventListener('change', atualizarPosicao);
        inputPosZ?.addEventListener('change', atualizarPosicao);

        // Botões de Camada (Z-Index)
        document.getElementById('btn-prop-z-avancar')?.addEventListener('click', async () => {
            if (this.editor.canvasLivreManager) {
                await this.editor.canvasLivreManager.alterarZIndex(id, 'forward');
                this.renderizarPropriedadesElemento(id, el);
                this.editor.atualizarPainelCamadas();
            }
        });
        document.getElementById('btn-prop-z-recuar')?.addEventListener('click', async () => {
            if (this.editor.canvasLivreManager) {
                await this.editor.canvasLivreManager.alterarZIndex(id, 'backward');
                this.renderizarPropriedadesElemento(id, el);
                this.editor.atualizarPainelCamadas();
            }
        });
        document.getElementById('btn-prop-z-frente')?.addEventListener('click', async () => {
            if (this.editor.canvasLivreManager) {
                await this.editor.canvasLivreManager.alterarZIndex(id, 'front');
                this.renderizarPropriedadesElemento(id, el);
                this.editor.atualizarPainelCamadas();
            }
        });
        document.getElementById('btn-prop-z-fundo')?.addEventListener('click', async () => {
            if (this.editor.canvasLivreManager) {
                await this.editor.canvasLivreManager.alterarZIndex(id, 'back');
                this.renderizarPropriedadesElemento(id, el);
                this.editor.atualizarPainelCamadas();
            }
        });

        // Estilos
        ['cor_texto', 'cor_fundo', 'sombra', 'animacao'].forEach(chave => {
            const input = document.getElementById(`prop-estilo-${chave}`);
            if (input) {
                input.addEventListener('change', (e) => {
                    const valor = e.target.value;
                    const estilos = {};
                    estilos[this.escopoAtivo] = {};
                    estilos[this.escopoAtivo][chave] = valor;

                    if (chave === 'cor_texto') el.style.color = valor;
                    if (chave === 'cor_fundo') el.style.backgroundColor = valor;

                    this.editor.autosaveManager.agendarSalvamento({
                        elemento_id: id,
                        estilos: estilos,
                    });
                });
            }
        });

        // Ações de Duplicar e Excluir
        document.getElementById('btn-prop-duplicar')?.addEventListener('click', () => {
            this.editor.duplicarElemento(id);
        });
        document.getElementById('btn-prop-excluir')?.addEventListener('click', () => {
            this.editor.excluirElemento(id);
        });
    }

    renderizarPropriedadesSecao(id, el) {
        const nomeAtual = el.querySelector('.editor-secao-nome')?.innerText || 'Seção';
        const tipoAtual = el.dataset.tipo || 'NORMAL';
        const modoCanvas = el.dataset.modoCanvas || 'livre';

        this.conteudoEl.innerHTML = `
            <div class="propriedades-header">
                <span class="propriedades-titulo">Seção #${id}</span>
            </div>
            <div class="propriedades-form">
                <div class="form-group-prop">
                    <label class="prop-label">Nome Interno</label>
                    <input type="text" class="prop-input" id="prop-secao-nome" value="${this.escapeHtml(nomeAtual)}">
                </div>

                <div class="form-group-prop">
                    <label class="prop-label">Modo de Criação</label>
                    <select class="prop-select" id="prop-secao-modo_canvas">
                        <option value="livre" ${modoCanvas === 'livre' ? 'selected' : ''}>🎨 Canvas Livre (Canva / Paint)</option>
                        <option value="fluxo" ${modoCanvas === 'fluxo' ? 'selected' : ''}>📑 Modo Fluxo Estruturado</option>
                    </select>
                </div>

                <div class="form-group-prop">
                    <label class="prop-label">Tipo de Seção</label>
                    <select class="prop-select" id="prop-secao-tipo">
                        <option value="normal" ${tipoAtual.toLowerCase() === 'normal' ? 'selected' : ''}>Normal (Conteúdo)</option>
                        <option value="altura_minima" ${tipoAtual.toLowerCase() === 'altura_minima' ? 'selected' : ''}>Altura Mínima</option>
                        <option value="tela_cheia" ${tipoAtual.toLowerCase() === 'tela_cheia' ? 'selected' : ''}>Tela Cheia (100vh)</option>
                    </select>
                </div>

                <div style="margin-top: 1rem; padding-top: 1rem; border-top: 1px solid var(--studio-border); display: flex; justify-content: space-between;">
                    <button type="button" class="btn-acao-elem" id="btn-secao-duplicar">⎘ Duplicar Seção</button>
                    <button type="button" class="btn-acao-elem btn-danger" id="btn-secao-excluir">✕ Excluir Seção</button>
                </div>
            </div>
        `;

        document.getElementById('prop-secao-nome')?.addEventListener('change', (e) => {
            const novoNome = e.target.value;
            const nomeEl = el.querySelector('.editor-secao-nome');
            if (nomeEl) nomeEl.innerText = novoNome;
            this.editor.salvarSecao(id, { nome_interno: novoNome });
        });

        document.getElementById('prop-secao-modo_canvas')?.addEventListener('change', (e) => {
            const novoModo = e.target.value;
            el.dataset.modoCanvas = novoModo;
            this.editor.salvarSecao(id, { estilos: { modo_canvas: novoModo } });
            location.reload(); // Recarrega para alternar os containers
        });

        document.getElementById('prop-secao-tipo')?.addEventListener('change', (e) => {
            this.editor.salvarSecao(id, { tipo: e.target.value });
        });

        document.getElementById('btn-secao-duplicar')?.addEventListener('click', () => {
            this.editor.duplicarSecao(id);
        });
        document.getElementById('btn-secao-excluir')?.addEventListener('click', () => {
            this.editor.excluirSecao(id);
        });
    }

    renderizarPropriedadesContainer(id, el) {
        const layoutAtual = el.dataset.layout || 'stack';

        this.conteudoEl.innerHTML = `
            <div class="propriedades-header">
                <span class="propriedades-titulo">Container #${id}</span>
            </div>
            <div class="propriedades-form">
                <div class="form-group-prop">
                    <label class="prop-label">Tipo de Layout</label>
                    <select class="prop-select" id="prop-container-layout">
                        <option value="stack" ${layoutAtual.toLowerCase() === 'stack' ? 'selected' : ''}>Pilha Vertical (Stack)</option>
                        <option value="row" ${layoutAtual.toLowerCase() === 'row' ? 'selected' : ''}>Linha Horizontal (Row)</option>
                        <option value="grid" ${layoutAtual.toLowerCase() === 'grid' ? 'selected' : ''}>Grade (Grid 2 Colunas)</option>
                        <option value="overlay" ${layoutAtual.toLowerCase() === 'overlay' ? 'selected' : ''}>Sobreposição (Overlay)</option>
                    </select>
                </div>
            </div>
        `;
    }

    escapeHtml(str) {
        if (!str) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }
}
