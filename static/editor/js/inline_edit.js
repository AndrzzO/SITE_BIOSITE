/**
 * inline_edit.js — Edição Direta de Texto no Canvas via Duplo Clique
 */

export class InlineEditManager {
    constructor(editor) {
        this.editor = editor;
        this.elementoAtivo = null;

        this.initEventListeners();
    }

    initEventListeners() {
        const root = document.getElementById('biosite-canvas-root');
        if (!root) return;

        // Duplo clique para ativar edição inline em títulos e textos
        root.addEventListener('dblclick', (e) => {
            const elemWrapper = e.target.closest('.editor-elemento-wrapper');
            if (!elemWrapper) return;

            const tipo = elemWrapper.dataset.tipo;
            if (tipo === 'TITULO' || tipo === 'TEXTO') {
                const targetTextEl = elemWrapper.querySelector('.elemento-titulo, .elemento-texto');
                if (targetTextEl) {
                    this.iniciarEdicao(elemWrapper, targetTextEl, tipo);
                }
            }
        });
    }

    iniciarEdicao(wrapper, textEl, tipo) {
        if (this.elementoAtivo) {
            this.finalizarEdicao(this.elementoAtivo.textEl);
        }

        this.elementoAtivo = { wrapper, textEl, tipo, valorOriginal: textEl.innerText };

        textEl.setAttribute('contenteditable', 'true');
        textEl.classList.add('is-editing-inline');
        textEl.focus();

        // Seleciona todo o texto para facilitar digitação
        const range = document.createRange();
        range.selectNodeContents(textEl);
        const sel = window.getSelection();
        sel.removeAllRanges();
        sel.addRange(range);

        // Sanitização estrita ao colar: aceita exclusivamente texto puro
        textEl.onpaste = (e) => {
            e.preventDefault();
            const textoPuro = (e.clipboardData || window.clipboardData).getData('text/plain');
            document.execCommand('insertText', false, textoPuro);
        };

        // Tecla Enter
        textEl.onkeydown = (e) => {
            if (tipo === 'TITULO' && e.key === 'Enter') {
                e.preventDefault();
                textEl.blur(); // Finaliza edição no título ao teclar Enter
            } else if (e.key === 'Escape') {
                e.preventDefault();
                textEl.innerText = this.elementoAtivo.valorOriginal; // Reverte alteração
                textEl.blur();
            }
        };

        // Finaliza ao perder o foco
        textEl.onblur = () => {
            this.finalizarEdicao(textEl);
        };
    }

    finalizarEdicao(textEl) {
        if (!this.elementoAtivo) return;

        textEl.removeAttribute('contenteditable');
        textEl.classList.remove('is-editing-inline');
        textEl.onpaste = null;
        textEl.onkeydown = null;
        textEl.onblur = null;

        const novoTexto = textEl.innerText.trim();
        const elementoId = parseInt(this.elementoAtivo.wrapper.dataset.elementoId, 10);

        // Se o texto mudou, agenda autosave e adiciona ao histórico
        if (novoTexto !== this.elementoAtivo.valorOriginal) {
            if (this.editor.autosaveManager) {
                this.editor.autosaveManager.agendarSalvamento({
                    elemento_id: elementoId,
                    conteudo: { texto: novoTexto }
                });
            }

            if (this.editor.historicoManager) {
                this.editor.historicoManager.registrarAcao('Edição de Texto', {
                    tipo: 'elemento',
                    id: elementoId,
                    anterior: { conteudo: { texto: this.elementoAtivo.valorOriginal } },
                    novo: { conteudo: { texto: novoTexto } }
                });
            }
        }

        this.elementoAtivo = null;
    }
}
