/**
 * propriedades.js — Painel Lateral Contextual de Propriedades e Estilos Mobile-First
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
        const tipoElem = el.dataset.tipo;
        const textoAtual = el.querySelector('.elemento-titulo, .elemento-texto, .elemento-botao')?.innerText || '';
        const urlAtual = el.querySelector('a')?.getAttribute('href') || '';

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
                    <label class="prop-label">Cor de Fundo do Botão</label>
                    <input type="color" class="prop-input" id="prop-estilo-cor_fundo" value="#2563eb" style="height: 38px; padding: 2px;">
                </div>
                <div class="form-group-prop">
                    <label class="prop-label">Cor do Texto</label>
                    <input type="color" class="prop-input" id="prop-estilo-cor_texto" value="#ffffff" style="height: 38px; padding: 2px;">
                </div>
                <div class="form-group-prop">
                    <label class="prop-label">Arredondamento da Borda (px)</label>
                    <input type="number" class="prop-input" id="prop-estilo-raio_borda" value="8" min="0" max="50">
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
        } else if (tipoElem === 'IMAGEM') {
            camposEspecificosHtml = `
                <div class="form-group-prop">
                    <label class="prop-label">URL da Imagem</label>
                    <input type="text" class="prop-input" id="prop-campo-url" placeholder="https://exemplo.com/foto.jpg">
                </div>
                <div class="form-group-prop">
                    <label class="prop-label">Texto Alternativo (Alt)</label>
                    <input type="text" class="prop-input" id="prop-campo-alt" placeholder="Descrição acessível da imagem">
                </div>
            `;
        }

        this.conteudoEl.innerHTML = `
            <div class="propriedades-header">
                <span class="propriedades-titulo">${tipoElem}</span>
                <div style="display: flex; gap: 0.3rem;">
                    <button type="button" class="btn-acao-elem ${this.escopoAtivo === 'base' ? 'is-selected' : ''}" id="btn-escopo-mobile" title="Edita base mobile (390px)">📱 Mobile</button>
                    <button type="button" class="btn-acao-elem ${this.escopoAtivo === 'desktop' ? 'is-selected' : ''}" id="btn-escopo-desktop" title="Override para telas amplas">🖥 Desktop</button>
                </div>
            </div>
            <div class="propriedades-form">
                ${camposEspecificosHtml}

                <div class="form-group-prop">
                    <label class="prop-label">Alinhamento do Texto</label>
                    <div class="prop-btn-group" id="group-alinhamento">
                        <button type="button" data-val="left">Esq</button>
                        <button type="button" data-val="center">Centro</button>
                        <button type="button" data-val="right">Dir</button>
                    </div>
                </div>

                <div class="form-group-prop">
                    <label class="prop-label">Tamanho da Fonte (px)</label>
                    <input type="number" class="prop-input" id="prop-estilo-tamanho_fonte" min="10" max="96" placeholder="Padrão">
                </div>

                <div class="form-group-prop">
                    <label class="prop-label">Cor do Texto</label>
                    <input type="color" class="prop-input" id="prop-estilo-cor_texto" style="height: 38px; padding: 2px;">
                </div>

                <div style="margin-top: 1rem; padding-top: 1rem; border-top: 1px solid var(--studio-border); display: flex; justify-content: space-between;">
                    <button type="button" class="btn-acao-elem" id="btn-prop-duplicar">⎘ Duplicar</button>
                    <button type="button" class="btn-acao-elem btn-danger" id="btn-prop-excluir">✕ Excluir</button>
                </div>
            </div>
        `;

        this.vincularEventosElemento(id, el, tipoElem);
    }

    vincularEventosElemento(id, el, tipoElem) {
        // Alternador de Escopo Mobile / Desktop
        document.getElementById('btn-escopo-mobile')?.addEventListener('click', () => {
            this.escopoAtivo = 'base';
            this.renderizarPropriedadesElemento(id, el);
        });
        document.getElementById('btn-escopo-desktop')?.addEventListener('click', () => {
            this.escopoAtivo = 'desktop';
            this.renderizarPropriedadesElemento(id, el);
        });

        // Eventos de Conteúdo
        const inputTexto = document.getElementById('prop-campo-texto');
        if (inputTexto) {
            inputTexto.addEventListener('input', (e) => {
                const novoTexto = e.target.value;
                const textoAlvo = el.querySelector('.elemento-titulo, .elemento-texto, .elemento-botao');
                if (textoAlvo) textoAlvo.innerText = novoTexto;

                this.editor.autosaveManager.agendarSalvamento({
                    elemento_id: id,
                    conteudo: { texto: novoTexto }
                });
            });
        }

        const inputUrl = document.getElementById('prop-campo-url');
        if (inputUrl) {
            inputUrl.addEventListener('change', (e) => {
                const novaUrl = e.target.value;
                this.editor.autosaveManager.agendarSalvamento({
                    elemento_id: id,
                    conteudo: { url: novaUrl }
                });
            });
        }

        // Eventos de Estilo
        const inputsEstilo = ['tamanho_fonte', 'cor_texto', 'cor_fundo', 'raio_borda'];
        inputsEstilo.forEach(chave => {
            const input = document.getElementById(`prop-estilo-${chave}`);
            if (input) {
                input.addEventListener('input', (e) => {
                    const valor = e.target.value;
                    const estilos = {};
                    estilos[this.escopoAtivo] = {};
                    estilos[this.escopoAtivo][chave] = valor;

                    // Atualiza em tempo real no elemento
                    if (chave === 'tamanho_fonte') el.style.fontSize = `${valor}px`;
                    if (chave === 'cor_texto') el.style.color = valor;
                    if (chave === 'cor_fundo') el.style.backgroundColor = valor;

                    this.editor.autosaveManager.agendarSalvamento({
                        elemento_id: id,
                        estilos: estilos
                    });
                });
            }
        });

        // Botões de Ação
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
                    <label class="prop-label">Tipo de Seção</label>
                    <select class="prop-select" id="prop-secao-tipo">
                        <option value="NORMAL" ${tipoAtual === 'NORMAL' ? 'selected' : ''}>Normal (Conteúdo)</option>
                        <option value="ALTURA_MINIMA" ${tipoAtual === 'ALTURA_MINIMA' ? 'selected' : ''}>Altura Mínima</option>
                        <option value="TELA_CHEIA" ${tipoAtual === 'TELA_CHEIA' ? 'selected' : ''}>Tela Cheia (100vh)</option>
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
        const layoutAtual = el.dataset.layout || 'STACK';

        this.conteudoEl.innerHTML = `
            <div class="propriedades-header">
                <span class="propriedades-titulo">Container #${id}</span>
            </div>
            <div class="propriedades-form">
                <div class="form-group-prop">
                    <label class="prop-label">Tipo de Layout</label>
                    <select class="prop-select" id="prop-container-layout">
                        <option value="STACK" ${layoutAtual === 'STACK' ? 'selected' : ''}>Pilha Vertical (Stack)</option>
                        <option value="ROW" ${layoutAtual === 'ROW' ? 'selected' : ''}>Linha Horizontal (Row)</option>
                        <option value="GRID" ${layoutAtual === 'GRID' ? 'selected' : ''}>Grade (Grid 2 Colunas)</option>
                        <option value="OVERLAY" ${layoutAtual === 'OVERLAY' ? 'selected' : ''}>Sobreposição (Overlay)</option>
                    </select>
                </div>
            </div>
        `;
    }

    escapeHtml(str) {
        if (!str) return '';
        return str
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }
}
