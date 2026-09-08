/**
 * editor.js — Orquestrador Central do Estúdio do Editor Visual
 */

import { EditorApi } from './api.js';
import { CanvasManager } from './canvas.js';
import { SelecaoManager } from './selecao.js';
import { InlineEditManager } from './inline_edit.js';
import { DragDropManager } from './dragdrop.js';
import { PropriedadesManager } from './propriedades.js';
import { AutosaveManager } from './autosave.js';
import { HistoricoManager } from './historico.js';

export class BioSiteEditorStudio {
    constructor(config) {
        this.siteUuid = config.siteUuid;
        this.paginaId = config.paginaId;

        this.canvasManager = null;
        this.selecaoManager = null;
        this.inlineEditManager = null;
        this.dragdropManager = null;
        this.propriedadesManager = null;
        this.autosaveManager = null;
        this.historicoManager = null;

        this.init();
    }

    init() {
        // Inicializa subsistemas
        this.canvasManager = new CanvasManager();
        this.propriedadesManager = new PropriedadesManager(this);
        this.selecaoManager = new SelecaoManager(this);
        this.inlineEditManager = new InlineEditManager(this);
        this.dragdropManager = new DragDropManager(this);
        this.autosaveManager = new AutosaveManager(this);
        this.historicoManager = new HistoricoManager(this);

        this.initAbasSidebar();
        this.initAcoesSecoes();
        this.initTrocaPagina();
        this.initCriarPagina();
    }

    initAbasSidebar() {
        document.querySelectorAll('.sidebar-tab').forEach(tab => {
            tab.addEventListener('click', () => {
                document.querySelectorAll('.sidebar-tab').forEach(t => t.classList.remove('active'));
                document.querySelectorAll('.sidebar-tab-content').forEach(c => c.classList.remove('active'));

                tab.classList.add('active');
                const targetId = tab.dataset.tab;
                const contentEl = document.getElementById(targetId);
                if (contentEl) contentEl.classList.add('active');
            });
        });
    }

    initAcoesSecoes() {
        const root = document.getElementById('biosite-canvas-root');
        if (!root) return;

        // Adicionar seção via botão inline "+"
        root.addEventListener('click', async (e) => {
            const btnAddSecao = e.target.closest('.btn-add-secao-inline');
            if (btnAddSecao) {
                const ordemDepois = btnAddSecao.dataset.ordemDepois;
                await this.criarSecao('Nova Seção', 'NORMAL', ordemDepois);
                return;
            }

            // Duplicar seção
            const btnDupSecao = e.target.closest('.btn-acao-secao[data-acao="duplicar"]');
            if (btnDupSecao) {
                const secaoWrapper = btnDupSecao.closest('.editor-secao-wrapper');
                if (secaoWrapper) {
                    await this.duplicarSecao(secaoWrapper.dataset.secaoId);
                }
                return;
            }

            // Excluir seção
            const btnExcSecao = e.target.closest('.btn-acao-secao[data-acao="excluir"]');
            if (btnExcSecao) {
                const secaoWrapper = btnExcSecao.closest('.editor-secao-wrapper');
                if (secaoWrapper) {
                    if (confirm('Deseja realmente excluir esta seção e todos os seus elementos?')) {
                        await this.excluirSecao(secaoWrapper.dataset.secaoId);
                    }
                }
                return;
            }

            // Duplicar elemento
            const btnDupElem = e.target.closest('.btn-acao-elem[data-acao="duplicar"]');
            if (btnDupElem) {
                const elemWrapper = btnDupElem.closest('.editor-elemento-wrapper');
                if (elemWrapper) {
                    await this.duplicarElemento(elemWrapper.dataset.elementoId);
                }
                return;
            }

            // Excluir elemento
            const btnExcElem = e.target.closest('.btn-acao-elem[data-acao="excluir"]');
            if (btnExcElem) {
                const elemWrapper = btnExcElem.closest('.editor-elemento-wrapper');
                if (elemWrapper) {
                    await this.excluirElemento(elemWrapper.dataset.elementoId);
                }
            }
        });
    }

    initTrocaPagina() {
        document.querySelectorAll('.pagina-item').forEach(item => {
            item.addEventListener('click', async () => {
                const pagId = item.dataset.paginaId;
                if (pagId === this.paginaId) return;

                document.querySelectorAll('.pagina-item').forEach(p => p.classList.remove('active'));
                item.classList.add('active');
                await this.carregarPagina(pagId);
            });
        });
    }

    initCriarPagina() {
        const btnNovaPag = document.getElementById('btn-nova-pagina');
        if (!btnNovaPag) return;

        btnNovaPag.addEventListener('click', async () => {
            const titulo = prompt('Título da nova página:');
            if (!titulo || !titulo.trim()) return;

            try {
                this.mostrarStatusSalvando();
                const resp = await EditorApi.fetchJson(`/painel/sites/${this.siteUuid}/editor/pagina/criar/`, {
                    method: 'POST',
                    body: JSON.stringify({ titulo: titulo.trim() })
                });

                // Adiciona na lista da sidebar
                const lista = document.getElementById('paginas-lista');
                if (lista) {
                    const novaLinha = document.createElement('div');
                    novaLinha.className = 'pagina-item';
                    novaLinha.dataset.paginaId = resp.pagina_id;
                    novaLinha.innerHTML = `<span>📄 ${resp.titulo}</span><span style="font-size:0.75rem; color:#94a3b8;">/${resp.slug}</span>`;
                    novaLinha.addEventListener('click', () => this.carregarPagina(resp.pagina_id));
                    lista.appendChild(novaLinha);
                }

                await this.carregarPagina(resp.pagina_id);
                this.mostrarStatusSalvo();
            } catch (err) {
                this.mostrarStatusErro(err.message);
            }
        });
    }

    async carregarPagina(paginaId) {
        try {
            this.mostrarStatusSalvando();
            const dados = await EditorApi.obterDados(this.siteUuid, paginaId);
            this.paginaId = paginaId;

            const canvasContainer = document.getElementById('studio-canvas-root');
            if (canvasContainer) {
                canvasContainer.outerHTML = dados.html_canvas;
            }

            // Reinicializa seletores e SortableJS na nova árvore
            this.dragdropManager.init();
            this.selecaoManager.desmarcar();
            this.mostrarStatusSalvo();
        } catch (err) {
            this.mostrarStatusErro(err.message);
        }
    }

    async criarSecao(nomeInterno = 'Nova Seção', tipo = 'NORMAL') {
        try {
            this.mostrarStatusSalvando();
            const resp = await EditorApi.criarSecao(this.siteUuid, {
                pagina_id: this.paginaId,
                nome_interno: nomeInterno,
                tipo: tipo
            });

            const secoesContainer = document.getElementById('editor-secoes-container');
            if (secoesContainer) {
                const avisoVazio = secoesContainer.querySelector('.editor-pagina-vazia');
                if (avisoVazio) avisoVazio.remove();

                secoesContainer.insertAdjacentHTML('beforeend', resp.html);
            }

            this.dragdropManager.init();
            this.mostrarStatusSalvo();
        } catch (err) {
            this.mostrarStatusErro(err.message);
        }
    }

    async duplicarSecao(secaoId) {
        try {
            this.mostrarStatusSalvando();
            const resp = await EditorApi.duplicarSecao(this.siteUuid, secaoId);
            const secaoOrig = document.querySelector(`.editor-secao-wrapper[data-secao-id="${secaoId}"]`);
            if (secaoOrig) {
                secaoOrig.insertAdjacentHTML('afterend', resp.html);
            }
            this.dragdropManager.init();
            this.mostrarStatusSalvo();
        } catch (err) {
            this.mostrarStatusErro(err.message);
        }
    }

    async excluirSecao(secaoId) {
        try {
            this.mostrarStatusSalvando();
            await EditorApi.excluirSecao(this.siteUuid, secaoId);
            const secaoEl = document.querySelector(`.editor-secao-wrapper[data-secao-id="${secaoId}"]`);
            if (secaoEl) secaoEl.remove();
            this.selecaoManager.desmarcar();
            this.mostrarStatusSalvo();
        } catch (err) {
            this.mostrarStatusErro(err.message);
        }
    }

    async salvarSecao(secaoId, dados) {
        try {
            this.mostrarStatusSalvando();
            await EditorApi.salvarSecaoPropriedades(this.siteUuid, secaoId, dados);
            this.mostrarStatusSalvo();
        } catch (err) {
            this.mostrarStatusErro(err.message);
        }
    }

    async duplicarElemento(elementoId) {
        try {
            this.mostrarStatusSalvando();
            const resp = await EditorApi.duplicarElemento(this.siteUuid, elementoId);
            const elemOrig = document.querySelector(`.editor-elemento-wrapper[data-elemento-id="${elementoId}"]`);
            if (elemOrig) {
                elemOrig.insertAdjacentHTML('afterend', resp.html);
                const novoEl = elemOrig.parentElement.querySelector(`.editor-elemento-wrapper[data-elemento-id="${resp.elemento_id}"]`);
                if (novoEl) {
                    this.selecaoManager.selecionar('elemento', resp.elemento_id, novoEl);
                }
            }
            this.dragdropManager.initSortableContainers();
            this.mostrarStatusSalvo();
        } catch (err) {
            this.mostrarStatusErro(err.message);
        }
    }

    async excluirElemento(elementoId) {
        try {
            this.mostrarStatusSalvando();
            await EditorApi.excluirElemento(this.siteUuid, elementoId);
            const elemEl = document.querySelector(`.editor-elemento-wrapper[data-elemento-id="${elementoId}"]`);
            if (elemEl) elemEl.remove();
            this.selecaoManager.desmarcar();
            this.mostrarStatusSalvo();
        } catch (err) {
            this.mostrarStatusErro(err.message);
        }
    }

    duplicarSelecionado() {
        const sel = this.selecaoManager?.itemSelecionado;
        if (!sel) return;
        if (sel.tipo === 'elemento') this.duplicarElemento(sel.id);
        else if (sel.tipo === 'secao') this.duplicarSecao(sel.id);
    }

    excluirSelecionado() {
        const sel = this.selecaoManager?.itemSelecionado;
        if (!sel) return;
        if (sel.tipo === 'elemento') {
            this.excluirElemento(sel.id);
        } else if (sel.tipo === 'secao') {
            if (confirm('Excluir esta seção?')) this.excluirSecao(sel.id);
        }
    }

    recarregarPaginaAtiva() {
        this.carregarPagina(this.paginaId);
    }

    mostrarStatusSalvando() {
        this.autosaveManager?.definirStatus('salvando');
    }

    mostrarStatusSalvo() {
        this.autosaveManager?.definirStatus('salvo');
    }

    mostrarStatusErro(msg) {
        console.error('[Editor Studio] Erro:', msg);
        this.autosaveManager?.definirStatus('erro');
    }
}
