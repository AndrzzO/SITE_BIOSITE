/**
 * dragdrop.js — Orquestração de Drag-and-Drop com SortableJS e Paleta
 */

import { EditorApi } from './api.js';

export class DragDropManager {
    constructor(editor) {
        this.editor = editor;
        this.sortablesSecoes = null;
        this.sortablesContainers = [];

        this.init();
    }

    init() {
        this.initSortableSecoes();
        this.initSortableContainers();
        this.initPaletaCliques();
    }

    initSortableSecoes() {
        const secoesContainer = document.getElementById('editor-secoes-container');
        if (!secoesContainer || typeof window.Sortable === 'undefined') return;

        if (this.sortablesSecoes) {
            this.sortablesSecoes.destroy();
        }

        this.sortablesSecoes = new window.Sortable(secoesContainer, {
            handle: '.editor-secao-drag-handle',
            draggable: '.editor-secao-wrapper',
            animation: 180,
            ghostClass: 'sortable-ghost',
            chosenClass: 'sortable-chosen',
            dragClass: 'sortable-drag',
            onEnd: async (evt) => {
                const ordemIds = Array.from(secoesContainer.querySelectorAll('.editor-secao-wrapper'))
                    .map(el => el.dataset.secaoId)
                    .filter(Boolean);

                const paginaId = document.getElementById('biosite-canvas-root')?.dataset.paginaId;
                if (!paginaId) return;

                try {
                    this.editor.mostrarStatusSalvando();
                    await EditorApi.moverSecoes(this.editor.siteUuid, {
                        pagina_id: paginaId,
                        ordem_ids: ordemIds
                    });
                    this.editor.mostrarStatusSalvo();
                } catch (err) {
                    this.editor.mostrarStatusErro(err.message);
                }
            }
        });
    }

    initSortableContainers() {
        if (typeof window.Sortable === 'undefined') return;

        // Limpa instâncias anteriores
        this.sortablesContainers.forEach(s => s.destroy());
        this.sortablesContainers = [];

        document.querySelectorAll('.sortable-container-elementos').forEach(containerEl => {
            const sortable = new window.Sortable(containerEl, {
                group: 'biosite-elementos', // Permite mover entre containers diferentes
                draggable: '.editor-elemento-wrapper',
                animation: 180,
                ghostClass: 'sortable-ghost',
                chosenClass: 'sortable-chosen',
                dragClass: 'sortable-drag',
                filter: '.is-editing-inline', // Não arrasta se estiver editando texto
                preventOnFilter: false,
                onEnd: async (evt) => {
                    const itemEl = evt.item;
                    const elementoId = itemEl.dataset.elementoId;
                    const novoContainerId = evt.to.dataset.containerId;

                    const ordemIds = Array.from(evt.to.querySelectorAll('.editor-elemento-wrapper'))
                        .map(el => el.dataset.elementoId)
                        .filter(Boolean);

                    try {
                        this.editor.mostrarStatusSalvando();
                        await EditorApi.moverElemento(this.editor.siteUuid, {
                            elemento_id: elementoId,
                            novo_container_id: novoContainerId,
                            ordem_ids: ordemIds
                        });
                        this.editor.mostrarStatusSalvo();
                    } catch (err) {
                        this.editor.mostrarStatusErro(err.message);
                    }
                }
            });

            this.sortablesContainers.push(sortable);
        });
    }

    initPaletaCliques() {
        // Clique em elemento da paleta insere no container selecionado ou no primeiro container disponível
        document.querySelectorAll('.paleta-item').forEach(item => {
            item.addEventListener('click', async () => {
                const tipo = item.dataset.tipo;
                let targetContainerId = null;

                const selecionado = this.editor.selecaoManager?.itemSelecionado;
                if (selecionado && selecionado.tipo === 'container') {
                    targetContainerId = selecionado.id;
                } else if (selecionado && selecionado.tipo === 'elemento') {
                    const containerPai = selecionado.el.closest('.editor-container-wrapper');
                    if (containerPai) targetContainerId = containerPai.dataset.containerId;
                }

                // Fallback: primeiro container da página
                if (!targetContainerId) {
                    const primeiro = document.querySelector('.editor-container-wrapper');
                    if (primeiro) targetContainerId = primeiro.dataset.containerId;
                }

                if (!targetContainerId) {
                    alert('Por favor, adicione ou selecione uma seção com container antes de inserir elementos.');
                    return;
                }

                await this.adicionarElemento(targetContainerId, tipo);
            });
        });
    }

    async adicionarElemento(containerId, tipo) {
        try {
            this.editor.mostrarStatusSalvando();
            const resp = await EditorApi.criarElemento(this.editor.siteUuid, {
                container_id: containerId,
                tipo: tipo
            });

            const dropzone = document.querySelector(`.sortable-container-elementos[data-container-id="${containerId}"]`);
            if (dropzone) {
                // Remove aviso de container vazio se existir
                const avisoVazio = dropzone.parentElement.querySelector('.editor-container-vazio');
                if (avisoVazio) avisoVazio.remove();

                dropzone.insertAdjacentHTML('beforeend', resp.html);
                const novoEl = dropzone.querySelector(`.editor-elemento-wrapper[data-elemento-id="${resp.elemento_id}"]`);
                if (novoEl) {
                    this.editor.selecaoManager.selecionar('elemento', resp.elemento_id, novoEl);
                    novoEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }
            }

            this.initSortableContainers();
            this.editor.mostrarStatusSalvo();
        } catch (err) {
            this.editor.mostrarStatusErro(err.message);
        }
    }
}
