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
import { CanvasLivreManager } from './canvas_livre.js';
import { HistoricoUndoManager } from './historico_undo.js';
import { HtmlImportManager } from './html_import.js';

export class BioSiteEditorStudio {
    constructor(config) {
        this.siteUuid = config.siteUuid;
        this.paginaId = config.paginaId;

        this.canvasManager      = null;
        this.selecaoManager     = null;
        this.inlineEditManager  = null;
        this.dragdropManager    = null;
        this.propriedadesManager = null;
        this.autosaveManager    = null;
        this.historicoManager   = null;
        this.canvasLivreManager = null;
        this.historicoUndo      = null;
        this.htmlImportManager  = null;

        this.init();
    }

    init() {
        // Inicializa subsistemas
        this.canvasManager       = new CanvasManager();
        this.propriedadesManager = new PropriedadesManager(this);
        this.selecaoManager      = new SelecaoManager(this);
        this.inlineEditManager   = new InlineEditManager(this);
        this.canvasLivreManager  = new CanvasLivreManager(this);
        this.historicoUndo       = new HistoricoUndoManager(this);
        this.dragdropManager     = new DragDropManager(this);
        this.autosaveManager     = new AutosaveManager(this);
        this.historicoManager    = new HistoricoManager(this);
        this.htmlImportManager   = new HtmlImportManager(this);

        this.initAbasSidebar();
        this.initAcoesSecoes();
        this.initTrocaPagina();
        this.initCriarPagina();
        this.initBlocosReutilizaveis();
        this.initSalvarComoModelo();
        this.initModalBloco();
        this.initPublicacao();
        this.initCanvasLivre();
        this.initControlesCanvasLivre();
        this.initPainelCamadas();
    }

    /**
     * Ativa o canvas livre em todas as seções que possuem data-modo-canvas="livre".
     * Chamado após o DOM renderizar (na init e após troca de página).
     */
    initCanvasLivre() {
        document.querySelectorAll('.editor-secao-wrapper[data-modo-canvas="livre"]').forEach(secaoEl => {
            this.canvasLivreManager.ativarSecao(secaoEl);
        });

        // Ativa drop zones em todas as canvas-livre-box existentes
        document.querySelectorAll('.canvas-livre-box').forEach(box => {
            if (this.dragdropManager) this.dragdropManager._initDropZone(box);
        });
    }

    /**
     * Inicializa botões da topbar/bottombar relacionados ao canvas livre:
     * Snap, Guias, Grade, Undo, Redo, Modo Livre/Fluxo, Alinhamento.
     */
    initControlesCanvasLivre() {
        // Snap
        const btnSnap = document.getElementById('btn-toggle-snap');
        if (btnSnap) btnSnap.addEventListener('click', () => {
            this.canvasLivreManager.toggleSnap();
            btnSnap.classList.toggle('active', this.canvasLivreManager.snapAtivo);
        });

        // Guias
        const btnGuias = document.getElementById('btn-toggle-guias');
        if (btnGuias) btnGuias.addEventListener('click', () => {
            this.canvasLivreManager.toggleGuias();
            btnGuias.classList.toggle('active', this.canvasLivreManager.guiasAtivas);
        });

        // Grade
        const btnGrade = document.getElementById('btn-toggle-grade');
        if (btnGrade) btnGrade.addEventListener('click', () => {
            this.canvasLivreManager.toggleGrade();
            btnGrade.classList.toggle('active', this.canvasLivreManager.gradeAtiva);
        });

        // Undo
        const btnDesfazer = document.getElementById('btn-desfazer');
        if (btnDesfazer) btnDesfazer.addEventListener('click', async () => {
            await this.historicoUndo.desfazer();
        });

        // Redo
        const btnRefazer = document.getElementById('btn-refazer');
        if (btnRefazer) btnRefazer.addEventListener('click', async () => {
            await this.historicoUndo.refazer();
        });

        // Alinhamento
        document.querySelectorAll('[data-alinhar]').forEach(btn => {
            btn.addEventListener('click', () => {
                const tipo = btn.dataset.alinhar;
                this.canvasLivreManager.alinhar(tipo);
            });
        });

        // Z-Index
        document.querySelectorAll('[data-zindex]').forEach(btn => {
            btn.addEventListener('click', async () => {
                const acao = btn.dataset.zindex;
                const sel  = this.selecaoManager?.itemSelecionado;
                if (sel?.tipo === 'elemento') {
                    await this.canvasLivreManager.alterarZIndex(sel.id, acao);
                    this.atualizarPainelCamadas();
                }
            });
        });
    }

    /**
     * Inicializa a sincronização do Painel de Camadas (Layers Panel)
     */
    initPainelCamadas() {
        const container = document.getElementById('layers-lista');
        if (!container) return;

        // Clique em um item da lista de camadas seleciona o elemento no canvas
        container.addEventListener('click', (e) => {
            const item = e.target.closest('.layer-item');
            if (!item) return;

            const elemId = parseInt(item.dataset.elementoId, 10);
            const elemEl = document.querySelector(`.editor-elemento-wrapper[data-elemento-id="${elemId}"]`);
            if (elemEl && this.selecaoManager) {
                this.selecaoManager.selecionar('elemento', elemId, elemEl);
                elemEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
        });
    }

    /**
     * Reconstrói a lista de camadas para a seção ativa
     */
    atualizarPainelCamadas() {
        const container = document.getElementById('layers-lista');
        if (!container) return;

        const secaoAtiva = document.querySelector('.editor-secao-wrapper');
        if (!secaoAtiva) {
            container.innerHTML = '<div style="color: var(--studio-text-muted); font-size: 0.8125rem; text-align: center; padding: 1rem 0;">Nenhuma seção ativa</div>';
            return;
        }

        const elementos = Array.from(secaoAtiva.querySelectorAll('.editor-elemento-wrapper'));
        if (elementos.length === 0) {
            container.innerHTML = '<div style="color: var(--studio-text-muted); font-size: 0.8125rem; text-align: center; padding: 1rem 0;">Nenhum elemento nesta seção</div>';
            return;
        }

        // Ordena por z-index (crescente)
        elementos.sort((a, b) => {
            const za = parseInt(a.style.zIndex || a.dataset.zIndex || 1, 10);
            const zb = parseInt(b.style.zIndex || b.dataset.zIndex || 1, 10);
            return za - zb;
        });

        const selId = this.selecaoManager?.itemSelecionado?.id;

        const html = elementos.map(el => {
            const id = el.dataset.elementoId;
            const tipo = el.dataset.tipo || 'ELEMENTO';
            const badge = el.querySelector('.editor-elemento-badge')?.textContent || tipo;
            const z = el.style.zIndex || el.dataset.zIndex || 1;
            const ativo = (selId && parseInt(id, 10) === selId) ? 'active' : '';

            return `
                <div class="layer-item ${ativo}" data-elemento-id="${id}">
                    <div class="layer-item-info">
                        <span style="font-size: 0.85rem;">⬚</span>
                        <span title="${badge}">${badge}</span>
                    </div>
                    <span class="layer-item-z">Z: ${z}</span>
                </div>
            `;
        }).join('');

        container.innerHTML = html;
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

                if (targetId === 'tab-camadas') {
                    this.atualizarPainelCamadas();
                }
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

            // Salvar seção como bloco reutilizável
            const btnSalvarBloco = e.target.closest('.btn-acao-secao[data-acao="salvar-bloco"]');
            if (btnSalvarBloco) {
                const secaoWrapper = btnSalvarBloco.closest('.editor-secao-wrapper');
                if (secaoWrapper) {
                    this.abrirModalSalvarBloco(secaoWrapper.dataset.secaoId);
                }
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
            this.initCanvasLivre();
            this.selecaoManager.desmarcar();
            this.atualizarPainelCamadas();
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
                tipo: tipo,
                modo_canvas: 'livre'
            });

            const secoesContainer = document.getElementById('editor-secoes-container');
            if (secoesContainer) {
                const avisoVazio = secoesContainer.querySelector('.editor-pagina-vazia');
                if (avisoVazio) avisoVazio.remove();

                secoesContainer.insertAdjacentHTML('beforeend', resp.html);
            }

            this.dragdropManager.init();
            this.initCanvasLivre();
            this.atualizarPainelCamadas();
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
            this.initCanvasLivre();
            this.atualizarPainelCamadas();
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
            this.atualizarPainelCamadas();
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
            if (elemOrig && resp.html) {
                elemOrig.insertAdjacentHTML('afterend', resp.html);
                const novoEl = document.querySelector(`.editor-elemento-wrapper[data-elemento-id="${resp.elemento_id}"]`);
                if (novoEl && this.canvasLivreManager) {
                    const box = novoEl.closest('.canvas-livre-box');
                    if (box) this.canvasLivreManager._ativarElemento(novoEl, box);
                }
            }
            this.atualizarPainelCamadas();
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
            this.atualizarPainelCamadas();
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

    async initBlocosReutilizaveis() {
        const grid = document.getElementById('blocos-reutilizaveis-grid');
        if (!grid) return;

        try {
            const resp = await EditorApi.listarBlocos(this.siteUuid);
            if (!resp.blocos || resp.blocos.length === 0) {
                grid.innerHTML = '<div style="color: var(--studio-text-muted); font-size:0.8125rem; text-align:center; padding: 1rem 0;">Nenhum bloco cadastrado.</div>';
                return;
            }

            grid.innerHTML = resp.blocos.map(b => `
                <div class="bloco-card-item" data-bloco-id="${b.id}" data-bloco-nome="${b.nome}" title="Clique para inserir na página">
                    <div class="bloco-card-header">
                        <span class="bloco-card-categoria">${b.categoria_label || b.categoria}</span>
                        <span class="bloco-card-badge">${b.origem === 'sistema' ? 'Sistema' : 'Personalizado'}</span>
                    </div>
                    <span class="bloco-card-nome">${b.nome}</span>
                    <span class="bloco-card-desc">${b.descricao || 'Seção pré-configurada pronta para uso.'}</span>
                </div>
            `).join('');

            grid.querySelectorAll('.bloco-card-item').forEach(card => {
                card.addEventListener('click', async () => {
                    const blocoId = card.dataset.blocoId;
                    await this.inserirBloco(blocoId);
                });
            });
        } catch (err) {
            grid.innerHTML = `<div style="color: var(--studio-danger); font-size:0.8125rem;">Erro ao carregar blocos: ${err.message}</div>`;
        }
    }

    async inserirBloco(blocoId) {
        try {
            this.mostrarStatusSalvando();
            const resp = await EditorApi.inserirBloco(this.siteUuid, {
                bloco_id: blocoId,
                pagina_id: this.paginaId
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
            alert(`Não foi possível inserir o bloco: ${err.message}`);
        }
    }

    abrirModalSalvarBloco(secaoId) {
        const modal = document.getElementById('modal-salvar-bloco');
        const inputId = document.getElementById('bloco-modal-secao-id');
        const inputNome = document.getElementById('bloco-modal-nome');
        const secaoEl = document.querySelector(`.editor-secao-wrapper[data-secao-id="${secaoId}"]`);

        if (!modal || !inputId || !inputNome) return;

        inputId.value = secaoId;
        const nomeAtual = secaoEl?.querySelector('.editor-secao-nome')?.textContent?.trim() || '';
        inputNome.value = nomeAtual ? `Bloco - ${nomeAtual}` : 'Novo Bloco Reutilizável';

        modal.style.display = 'flex';
    }

    initModalBloco() {
        const modal = document.getElementById('modal-salvar-bloco');
        if (!modal) return;

        modal.querySelectorAll('[data-fechar-modal]').forEach(btn => {
            btn.addEventListener('click', () => {
                modal.style.display = 'none';
            });
        });

        const btnConfirmar = document.getElementById('btn-confirmar-salvar-bloco');
        if (btnConfirmar) {
            btnConfirmar.addEventListener('click', async () => {
                const secaoId = document.getElementById('bloco-modal-secao-id')?.value;
                const nome = document.getElementById('bloco-modal-nome')?.value?.trim();
                const categoria = document.getElementById('bloco-modal-categoria')?.value;
                const descricao = document.getElementById('bloco-modal-descricao')?.value?.trim();
                const sanitizar = document.getElementById('bloco-modal-sanitizar')?.checked;

                if (!nome) {
                    alert('Informe um nome para o bloco.');
                    return;
                }

                try {
                    btnConfirmar.disabled = true;
                    btnConfirmar.textContent = 'Salvando...';

                    const resp = await EditorApi.salvarSecaoComoBloco(this.siteUuid, secaoId, {
                        nome,
                        categoria,
                        descricao,
                        substituir_placeholders: sanitizar
                    });

                    modal.style.display = 'none';
                    alert(`Bloco "${resp.nome}" salvo com sucesso em Meus Blocos!`);
                    await this.initBlocosReutilizaveis();
                } catch (err) {
                    alert(`Erro ao salvar bloco: ${err.message}`);
                } finally {
                    btnConfirmar.disabled = false;
                    btnConfirmar.textContent = 'Salvar Bloco';
                }
            });
        }
    }

    initSalvarComoModelo() {
        const btnAbrir = document.getElementById('btn-salvar-template');
        const modal = document.getElementById('modal-salvar-template');
        if (!btnAbrir || !modal) return;

        btnAbrir.addEventListener('click', () => {
            const inputNome = document.getElementById('template-modal-nome');
            const tituloSite = document.querySelector('.studio-projeto-titulo')?.textContent?.trim() || '';
            if (inputNome && !inputNome.value) {
                inputNome.value = tituloSite ? `Modelo - ${tituloSite}` : 'Novo Modelo';
            }
            modal.style.display = 'flex';
        });

        modal.querySelectorAll('[data-fechar-modal]').forEach(btn => {
            btn.addEventListener('click', () => {
                modal.style.display = 'none';
            });
        });

        const btnConfirmar = document.getElementById('btn-confirmar-salvar-template');
        if (btnConfirmar) {
            btnConfirmar.addEventListener('click', async () => {
                const nome = document.getElementById('template-modal-nome')?.value?.trim();
                const categoria = document.getElementById('template-modal-categoria')?.value;
                const descricao = document.getElementById('template-modal-descricao')?.value?.trim();
                const sanitizar = document.getElementById('template-modal-sanitizar')?.checked;

                if (!nome) {
                    alert('Informe um nome para o modelo.');
                    return;
                }

                try {
                    btnConfirmar.disabled = true;
                    btnConfirmar.textContent = 'Salvando...';

                    const resp = await EditorApi.salvarProjetoComoTemplate(this.siteUuid, {
                        nome,
                        categoria,
                        descricao,
                        substituir_placeholders: sanitizar
                    });

                    modal.style.display = 'none';
                    if (confirm(`Modelo "${resp.nome}" criado com sucesso!\n\nDeseja abrir a Biblioteca de Templates agora?`)) {
                        window.location.href = resp.url_biblioteca;
                    }
                } catch (err) {
                    alert(`Erro ao salvar modelo: ${err.message}`);
                } finally {
                    btnConfirmar.disabled = false;
                    btnConfirmar.textContent = 'Salvar Modelo';
                }
            });
        }
    }

    initPublicacao() {
        // Carrega status inicial da publicação
        this.atualizarStatusPublicacao();

        // Botão "Publicar" no topo
        const btnPublicar = document.getElementById('btn-publicar-projeto');
        if (btnPublicar) {
            btnPublicar.addEventListener('click', () => this.abrirModalPublicar());
        }

        // Botão "Confirmar e Publicar" no modal
        const btnExecutar = document.getElementById('btn-executar-publicacao');
        if (btnExecutar) {
            btnExecutar.addEventListener('click', () => this.executarPublicacao());
        }

        // Botão "Copiar URL" no modal de sucesso
        const btnCopiar = document.getElementById('btn-copiar-url-sucesso');
        if (btnCopiar) {
            btnCopiar.addEventListener('click', () => {
                const urlInput = document.getElementById('pub-sucesso-url');
                if (urlInput) {
                    navigator.clipboard.writeText(urlInput.value);
                    const originalText = btnCopiar.textContent;
                    btnCopiar.textContent = '✓ Copiado!';
                    setTimeout(() => {
                        btnCopiar.textContent = originalText;
                    }, 2000);
                }
            });
        }

        // Botão "Histórico de Versões" no topo
        const btnHistorico = document.getElementById('btn-historico-versoes');
        if (btnHistorico) {
            btnHistorico.addEventListener('click', () => this.abrirModalHistorico());
        }

        // Botão "Despublicar" no modal de histórico
        const btnDespublicar = document.getElementById('btn-despublicar-editor');
        if (btnDespublicar) {
            btnDespublicar.addEventListener('click', () => this.despublicarProjeto());
        }
    }

    async atualizarStatusPublicacao() {
        const indicador = document.getElementById('publicacao-status-indicador');
        if (!indicador) return;

        try {
            const status = await EditorApi.obterStatusPublicacao(this.siteUuid);
            const textoEl = indicador.querySelector('.pub-status-texto');

            indicador.classList.remove('publicado', 'pendente', 'rascunho');

            if (status.publicado) {
                if (status.alteracoes_pendentes) {
                    indicador.classList.add('pendente');
                    if (textoEl) textoEl.textContent = `v${status.versao_atual} • Não publicado`;
                    indicador.title = `Site no ar na versão v${status.versao_atual}, mas há alterações pendentes no editor.`;
                } else {
                    indicador.classList.add('publicado');
                    if (textoEl) textoEl.textContent = `v${status.versao_atual} no ar`;
                    indicador.title = `Versão v${status.versao_atual} publicada e em sincronia com o site público.`;
                }
            } else {
                indicador.classList.add('rascunho');
                if (textoEl) textoEl.textContent = 'Rascunho';
                indicador.title = 'Site em modo rascunho. Não publicado na internet.';
            }
        } catch (err) {
            console.error('Erro ao verificar status de publicação:', err);
        }
    }

    async abrirModalPublicar() {
        const modal = document.getElementById('modal-confirmar-publicacao');
        const loading = document.getElementById('pub-loading-validacao');
        const conteudo = document.getElementById('pub-conteudo-validacao');
        const btnExecutar = document.getElementById('btn-executar-publicacao');
        const errosBox = document.getElementById('pub-erros-box');
        const errosLista = document.getElementById('pub-erros-lista');
        const avisosBox = document.getElementById('pub-avisos-box');
        const avisosLista = document.getElementById('pub-avisos-lista');

        if (!modal) return;

        modal.style.display = 'flex';
        if (loading) loading.style.display = 'block';
        if (conteudo) conteudo.style.display = 'none';
        if (btnExecutar) btnExecutar.disabled = true;

        try {
            const validacao = await EditorApi.validarPrePublicacao(this.siteUuid);

            if (loading) loading.style.display = 'none';
            if (conteudo) conteudo.style.display = 'block';

            // Erros bloqueantes
            if (errosBox && errosLista) {
                if (validacao.erros && validacao.erros.length > 0) {
                    errosLista.innerHTML = validacao.erros.map(e => `<li>${e}</li>`).join('');
                    errosBox.style.display = 'block';
                    if (btnExecutar) btnExecutar.disabled = true;
                } else {
                    errosBox.style.display = 'none';
                    if (btnExecutar) btnExecutar.disabled = false;
                }
            }

            // Avisos não-bloqueantes
            if (avisosBox && avisosLista) {
                if (validacao.avisos && validacao.avisos.length > 0) {
                    avisosLista.innerHTML = validacao.avisos.map(a => `<li>${a}</li>`).join('');
                    avisosBox.style.display = 'block';
                    if (btnExecutar && !btnExecutar.disabled) {
                        btnExecutar.textContent = '🚀 Confirmar Publicação (com Avisos)';
                    }
                } else {
                    avisosBox.style.display = 'none';
                    if (btnExecutar && !btnExecutar.disabled) {
                        btnExecutar.textContent = '🚀 Confirmar e Publicar Agora';
                    }
                }
            }
        } catch (err) {
            if (loading) loading.textContent = `Erro ao validar: ${err.message}`;
        }
    }

    async executarPublicacao() {
        const modalConfirmar = document.getElementById('modal-confirmar-publicacao');
        const modalSucesso = document.getElementById('modal-sucesso-publicacao');
        const btnExecutar = document.getElementById('btn-executar-publicacao');

        try {
            if (btnExecutar) {
                btnExecutar.disabled = true;
                btnExecutar.textContent = 'Gerando snapshot imutável...';
            }

            const resp = await EditorApi.publicarProjeto(this.siteUuid, true);

            if (modalConfirmar) modalConfirmar.style.display = 'none';

            // Atualiza tags de status
            await this.atualizarStatusPublicacao();

            // Abre modal de sucesso
            if (modalSucesso) {
                const versaoEl = document.getElementById('pub-sucesso-versao');
                const urlEl = document.getElementById('pub-sucesso-url');
                const linkAbrir = document.getElementById('btn-abrir-site-sucesso');

                if (versaoEl) versaoEl.textContent = `v${resp.versao}`;
                if (urlEl) urlEl.value = resp.url_publica;
                if (linkAbrir) linkAbrir.href = resp.url_publica;

                modalSucesso.style.display = 'flex';
            }
        } catch (err) {
            alert(`Erro ao publicar projeto: ${err.message}`);
        } finally {
            if (btnExecutar) {
                btnExecutar.disabled = false;
                btnExecutar.textContent = '🚀 Confirmar e Publicar';
            }
        }
    }

    async abrirModalHistorico() {
        const modal = document.getElementById('modal-historico-publicacoes');
        const loading = document.getElementById('pub-historico-loading');
        const container = document.getElementById('pub-historico-tabela-container');
        const vazio = document.getElementById('pub-historico-vazio');
        const tbody = document.getElementById('pub-historico-tbody');
        const btnDespublicar = document.getElementById('btn-despublicar-editor');

        if (!modal) return;
        modal.style.display = 'flex';
        if (loading) loading.style.display = 'block';
        if (container) container.style.display = 'none';
        if (vazio) vazio.style.display = 'none';

        try {
            const resp = await EditorApi.listarHistoricoPublicacoes(this.siteUuid);
            if (loading) loading.style.display = 'none';

            if (!resp.publicacoes || resp.publicacoes.length === 0) {
                if (vazio) vazio.style.display = 'block';
                if (btnDespublicar) btnDespublicar.style.display = 'none';
                return;
            }

            let temAtiva = false;
            if (tbody) {
                tbody.innerHTML = resp.publicacoes.map(p => {
                    if (p.ativa) temAtiva = true;
                    const statusHtml = p.ativa
                        ? '<span style="color: #34d399; font-weight: 700;">● No Ar</span>'
                        : '<span style="color: #94a3b8;">Histórico</span>';

                    const acaoRestaurar = !p.ativa
                        ? `<button type="button" class="btn-preview btn-rollback-versao" data-versao="${p.numero_versao}" style="padding: 0.25rem 0.5rem; font-size: 0.75rem;" title="Criar nova versão com este snapshot e colocar no ar">↺ Restaurar no Ar</button>
                           <button type="button" class="btn-acao-elem btn-restaurar-editor" data-versao="${p.numero_versao}" style="padding: 0.25rem 0.5rem; font-size: 0.75rem;" title="Substituir rascunho atual do editor pelo conteúdo desta versão">Editar Esta</button>`
                        : '';

                    return `
                        <tr>
                            <td style="font-weight: 700; color: var(--studio-accent);">${p.versao_label}</td>
                            <td>${statusHtml}</td>
                            <td style="color: var(--studio-text-muted);">${p.publicado_em}</td>
                            <td style="color: var(--studio-text-muted);">${p.autor}</td>
                            <td><code style="font-size: 0.75rem;">${p.hash_curto}</code></td>
                            <td style="text-align: right;">
                                <div style="display: inline-flex; gap: 0.35rem; align-items: center;">
                                    <a href="${p.url_preview}" target="_blank" class="btn-preview" style="padding: 0.25rem 0.5rem; font-size: 0.75rem;">Preview</a>
                                    ${acaoRestaurar}
                                </div>
                            </td>
                        </tr>
                    `;
                }).join('');

                // Adiciona listeners para os botões dinâmicos
                tbody.querySelectorAll('.btn-rollback-versao').forEach(btn => {
                    btn.addEventListener('click', async () => {
                        const versao = btn.dataset.versao;
                        if (!confirm(`Deseja restaurar a versão v${versao}? Uma nova versão estável será criada e colocada imediatamente no ar.`)) {
                            return;
                        }
                        try {
                            btn.disabled = true;
                            await EditorApi.rollbackPublicacao(this.siteUuid, versao);
                            alert(`Rollback concluído! Versão v${versao} restaurada e colocada no ar com sucesso.`);
                            await this.atualizarStatusPublicacao();
                            await this.abrirModalHistorico();
                        } catch (err) {
                            alert(`Erro ao realizar rollback: ${err.message}`);
                        } finally {
                            btn.disabled = false;
                        }
                    });
                });

                tbody.querySelectorAll('.btn-restaurar-editor').forEach(btn => {
                    btn.addEventListener('click', async () => {
                        const versao = btn.dataset.versao;
                        if (!confirm(`ATENÇÃO: Deseja carregar o conteúdo da versão v${versao} no editor? Seu rascunho de trabalho atual será substituído por este snapshot.`)) {
                            return;
                        }
                        try {
                            btn.disabled = true;
                            await EditorApi.restaurarVersaoEditor(this.siteUuid, versao);
                            alert(`Conteúdo da versão v${versao} restaurado no editor! A página será recarregada.`);
                            window.location.reload();
                        } catch (err) {
                            alert(`Erro ao sincronizar editor: ${err.message}`);
                            btn.disabled = false;
                        }
                    });
                });
            }

            if (container) container.style.display = 'block';
            if (btnDespublicar) btnDespublicar.style.display = temAtiva ? 'inline-block' : 'none';
        } catch (err) {
            if (loading) loading.textContent = `Erro ao carregar histórico: ${err.message}`;
        }
    }

    async despublicarProjeto() {
        if (!confirm('Deseja realmente despublicar o site? Ele deixará de responder no ar imediatamente (retornando 404), mas todo o histórico e rascunho serão preservados.')) {
            return;
        }

        const btn = document.getElementById('btn-despublicar-editor');
        try {
            if (btn) btn.disabled = true;
            await EditorApi.despublicarProjeto(this.siteUuid);
            alert('Site despublicado com sucesso.');
            await this.atualizarStatusPublicacao();
            const modal = document.getElementById('modal-historico-publicacoes');
            if (modal) modal.style.display = 'none';
        } catch (err) {
            alert(`Erro ao despublicar: ${err.message}`);
        } finally {
            if (btn) btn.disabled = false;
        }
    }
}
