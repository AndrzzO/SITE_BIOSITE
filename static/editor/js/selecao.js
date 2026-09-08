/**
 * selecao.js — Gerenciador de Seleção Única no Canvas e Sincronização
 */

export class SelecaoManager {
    constructor(editor) {
        this.editor = editor;
        this.itemSelecionado = null; // { tipo: 'elemento' | 'container' | 'secao', id: number, el: HTMLElement }

        this.initEventListeners();
    }

    initEventListeners() {
        const root = document.getElementById('biosite-canvas-root');
        if (!root) return;

        // Clique no Canvas com delegação de eventos
        root.addEventListener('click', (e) => {
            // Ignora se for clique em botão de ação do wrapper
            if (e.target.closest('.btn-acao-elem, .btn-acao-secao, .btn-acao-container, .btn-add-secao-inline')) {
                return;
            }

            // 1. Elemento
            const elemEl = e.target.closest('.editor-elemento-wrapper');
            if (elemEl) {
                e.stopPropagation();
                this.selecionar('elemento', parseInt(elemEl.dataset.elementoId, 10), elemEl);
                return;
            }

            // 2. Container
            const contEl = e.target.closest('.editor-container-wrapper');
            if (contEl) {
                e.stopPropagation();
                this.selecionar('container', parseInt(contEl.dataset.containerId, 10), contEl);
                return;
            }

            // 3. Seção
            const secEl = e.target.closest('.editor-secao-wrapper');
            if (secEl) {
                e.stopPropagation();
                this.selecionar('secao', parseInt(secEl.dataset.secaoId, 10), secEl);
                return;
            }

            // Clique no vazio do canvas
            this.desmarcar();
        });

        // Clique fora do canvas (no fundo cinza da área de trabalho)
        const canvasArea = document.querySelector('.studio-canvas-area');
        if (canvasArea) {
            canvasArea.addEventListener('click', (e) => {
                if (e.target === canvasArea) {
                    this.desmarcar();
                }
            });
        }
    }

    selecionar(tipo, id, el) {
        this.desmarcar(false); // Limpa seleção anterior sem fechar propriedades se mesmo tipo

        this.itemSelecionado = { tipo, id, el };
        if (el) {
            el.classList.add('is-selected');
            if (tipo === 'elemento' && el.closest('.canvas-livre-box')) {
                el.classList.add('canvas-selected');
                if (this.editor.canvasLivreManager) {
                    this.editor.canvasLivreManager.selecionados = [el];
                }
            }
        }

        // Notifica o painel de propriedades
        if (this.editor.propriedadesManager) {
            this.editor.propriedadesManager.carregarPropriedades(tipo, id, el);
        }

        // Sincroniza destaque na árvore de estrutura e no painel de camadas
        this.destacarNaArvore(tipo, id);
        if (this.editor.atualizarPainelCamadas) {
            this.editor.atualizarPainelCamadas();
        }
    }

    desmarcar(fecharPainel = true) {
        document.querySelectorAll('.is-selected, .canvas-selected, .canvas-multi-selected').forEach(el => {
            el.classList.remove('is-selected', 'canvas-selected', 'canvas-multi-selected');
        });

        if (this.editor.canvasLivreManager) {
            this.editor.canvasLivreManager.selecionados = [];
        }

        this.itemSelecionado = null;

        if (fecharPainel && this.editor.propriedadesManager) {
            this.editor.propriedadesManager.limpar();
        }

        document.querySelectorAll('.arvore-item.is-selected').forEach(el => {
            el.classList.remove('is-selected');
        });

        if (this.editor.atualizarPainelCamadas) {
            this.editor.atualizarPainelCamadas();
        }
    }

    destacarNaArvore(tipo, id) {
        document.querySelectorAll('.arvore-item').forEach(el => el.classList.remove('is-selected'));
        const itemArvore = document.querySelector(`.arvore-item[data-tipo="${tipo}"][data-id="${id}"]`);
        if (itemArvore) {
            itemArvore.classList.add('is-selected');
        }
    }
}
