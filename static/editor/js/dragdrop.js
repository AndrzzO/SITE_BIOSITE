import { EditorApi } from './api.js';

export class DragDropManager {
    constructor(editor) {
        this.editor = editor;
        this.sortablesSecoes     = null;
        this.sortablesContainers = [];
        this.init();
    }

    init() {
        this.initSortableSecoes();
        this.initSortableContainers();
        this.initPaletaCliques();
        this.initPaletaDragDrop();
    }

    initSortableSecoes() {
        const secoesContainer = document.getElementById('editor-secoes-container');
        if (!secoesContainer || typeof window.Sortable === 'undefined') return;
        if (this.sortablesSecoes) this.sortablesSecoes.destroy();

        this.sortablesSecoes = new window.Sortable(secoesContainer, {
            handle: '.editor-secao-drag-handle',
            draggable: '.editor-secao-wrapper',
            animation: 180,
            ghostClass: 'sortable-ghost',
            chosenClass: 'sortable-chosen',
            dragClass: 'sortable-drag',
            onEnd: async () => {
                const ordemIds = Array.from(secoesContainer.querySelectorAll('.editor-secao-wrapper'))
                    .map(el => el.dataset.secaoId).filter(Boolean);
                const paginaId = document.getElementById('biosite-canvas-root')?.dataset.paginaId;
                if (!paginaId) return;
                try {
                    this.editor.mostrarStatusSalvando();
                    await EditorApi.moverSecoes(this.editor.siteUuid, { pagina_id: paginaId, ordem_ids: ordemIds });
                    this.editor.mostrarStatusSalvo();
                } catch (err) { this.editor.mostrarStatusErro(err.message); }
            }
        });
    }

    initSortableContainers() {
        if (typeof window.Sortable === 'undefined') return;
        this.sortablesContainers.forEach(s => s.destroy());
        this.sortablesContainers = [];

        document.querySelectorAll('.sortable-container-elementos').forEach(containerEl => {
            const secaoWrapper = containerEl.closest('.editor-secao-wrapper');
            if (secaoWrapper?.dataset.modoCanvas === 'livre') return;

            const sortable = new window.Sortable(containerEl, {
                group: 'biosite-elementos',
                draggable: '.editor-elemento-wrapper',
                animation: 180,
                ghostClass: 'sortable-ghost',
                chosenClass: 'sortable-chosen',
                dragClass: 'sortable-drag',
                filter: '.is-editing-inline',
                preventOnFilter: false,
                onEnd: async (evt) => {
                    const elementoId      = evt.item.dataset.elementoId;
                    const novoContainerId = evt.to.dataset.containerId;
                    const ordemIds = Array.from(evt.to.querySelectorAll('.editor-elemento-wrapper'))
                        .map(el => el.dataset.elementoId).filter(Boolean);
                    try {
                        this.editor.mostrarStatusSalvando();
                        await EditorApi.moverElemento(this.editor.siteUuid, {
                            elemento_id: elementoId, novo_container_id: novoContainerId, ordem_ids: ordemIds
                        });
                        this.editor.mostrarStatusSalvo();
                    } catch (err) { this.editor.mostrarStatusErro(err.message); }
                }
            });
            this.sortablesContainers.push(sortable);
        });
    }

    initPaletaCliques() {
        document.querySelectorAll('.paleta-item').forEach(item => {
            item.addEventListener('click', async () => {
                const tipo = item.dataset.tipo;
                const secaoAtiva = this._getSecaoAtiva();
                if (secaoAtiva?.dataset.modoCanvas === 'livre') {
                    await this.adicionarElementoCanvasLivre(tipo, secaoAtiva, null, null);
                    return;
                }
                let targetContainerId = null;
                const selecionado = this.editor.selecaoManager?.itemSelecionado;
                if (selecionado?.tipo === 'container') {
                    targetContainerId = selecionado.id;
                } else if (selecionado?.tipo === 'elemento') {
                    const pai = selecionado.el.closest('.editor-container-wrapper');
                    if (pai) targetContainerId = pai.dataset.containerId;
                }
                if (!targetContainerId) {
                    const primeiro = document.querySelector('.editor-container-wrapper');
                    if (primeiro) targetContainerId = primeiro.dataset.containerId;
                }
                if (!targetContainerId) {
                    alert('Adicione ou selecione uma secao antes de inserir elementos.');
                    return;
                }
                await this.adicionarElemento(targetContainerId, tipo);
            });
        });
    }

    initPaletaDragDrop() {
        document.querySelectorAll('.paleta-item').forEach(item => {
            item.setAttribute('draggable', 'true');
            item.addEventListener('dragstart', (e) => {
                e.dataTransfer.setData('text/plain', item.dataset.tipo);
                e.dataTransfer.effectAllowed = 'copy';
            });
        });
        document.querySelectorAll('.canvas-livre-box').forEach(box => {
            this._initDropZone(box);
        });
    }

    _initDropZone(box) {
        box.addEventListener('dragover', (e) => {
            e.preventDefault();
            e.dataTransfer.dropEffect = 'copy';
            box.classList.add('canvas-drop-active');
        });
        box.addEventListener('dragleave', (e) => {
            if (!box.contains(e.relatedTarget)) box.classList.remove('canvas-drop-active');
        });
        box.addEventListener('drop', async (e) => {
            e.preventDefault();
            box.classList.remove('canvas-drop-active');
            const tipo = e.dataTransfer.getData('text/plain');
            if (!tipo) return;
            const boxRect  = box.getBoundingClientRect();
            const dropX    = e.clientX - boxRect.left;
            const dropY    = e.clientY - boxRect.top;
            const secaoWrapper = box.closest('.editor-secao-wrapper');
            if (secaoWrapper) await this.adicionarElementoCanvasLivre(tipo, secaoWrapper, dropX, dropY, box);
        });
    }

    async adicionarElemento(containerId, tipo) {
        try {
            this.editor.mostrarStatusSalvando();
            const resp = await EditorApi.criarElemento(this.editor.siteUuid, { container_id: containerId, tipo });
            const dropzone = document.querySelector(`.sortable-container-elementos[data-container-id="${containerId}"]`);
            if (dropzone) {
                dropzone.parentElement.querySelector('.editor-container-vazio')?.remove();
                dropzone.insertAdjacentHTML('beforeend', resp.html);
                const novoEl = dropzone.querySelector(`.editor-elemento-wrapper[data-elemento-id="${resp.elemento_id}"]`);
                if (novoEl) {
                    this.editor.selecaoManager.selecionar('elemento', resp.elemento_id, novoEl);
                    novoEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }
            }
            this.initSortableContainers();
            if (this.editor.historicoUndo) this.editor.historicoUndo.snapshot();
            this.editor.mostrarStatusSalvo();
        } catch (err) { this.editor.mostrarStatusErro(err.message); }
    }

    async adicionarElementoCanvasLivre(tipo, secaoWrapper, dropX, dropY, canvasBox = null) {
        const containerId = secaoWrapper.querySelector('[data-container-id]')?.dataset.containerId;
        if (!containerId) { alert('Secao sem container. Recarregue o editor.'); return; }
        const box = canvasBox || secaoWrapper.querySelector('.canvas-livre-box');
        if (!box) return;
        try {
            this.editor.mostrarStatusSalvando();
            const resp = await EditorApi.criarElemento(this.editor.siteUuid, { container_id: containerId, tipo });
            box.insertAdjacentHTML('beforeend', resp.html);
            const novoEl = box.querySelector(`.editor-elemento-wrapper[data-elemento-id="${resp.elemento_id}"]`);
            if (novoEl && this.editor.canvasLivreManager) {
                const pos = this.editor.canvasLivreManager.posicionarNovoElemento(novoEl, box, dropX, dropY);
                await this.editor.canvasLivreManager._persistirPosicao(resp.elemento_id, pos);
            }
            if (this.editor.historicoUndo) this.editor.historicoUndo.snapshot();
            this.editor.mostrarStatusSalvo();
        } catch (err) { this.editor.mostrarStatusErro(err.message); }
    }

    _getSecaoAtiva() {
        const sel = this.editor.selecaoManager?.itemSelecionado;
        if (sel?.tipo === 'secao' || sel?.tipo === 'elemento') {
            const secaoEl = sel.el.closest('.editor-secao-wrapper');
            if (secaoEl) return secaoEl;
        }
        return document.querySelector('.editor-secao-wrapper[data-modo-canvas="livre"]');
    }
}