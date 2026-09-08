/**
 * canvas_livre.js — Motor do Canvas Livre (Drag, Resize, Snap, Guides, Multi-Seleção)
 *
 * Responsabilidades:
 *  - Arrastar elementos no canvas com posicionamento absoluto
 *  - Redimensionar elementos pelos 8 handles
 *  - Smart guides / snap magnético (on/off)
 *  - Grid overlay (on/off)
 *  - Multi-seleção (SHIFT+CLICK, rect-selection)
 *  - Ferramentas de alinhamento (left, center, right, top, middle, bottom, H/V distribute)
 *  - Z-index (forward, backward, front, back)
 *  - Context menu de click-direito
 *  - Teclas de atalho: DEL, CTRL+D, CTRL+C, CTRL+V, setas
 */

import { EditorApi } from './api.js';

const SNAP_THRESHOLD = 8;     // px de magnetismo
const MIN_W = 40;             // largura mínima px
const MIN_H = 24;             // altura mínima px

export class CanvasLivreManager {
    constructor(editor) {
        this.editor = editor;

        // Estado do drag
        this._drag = null;
        // Estado do resize
        this._resize = null;

        // Seleção múltipla
        this.selecionados = new Set(); // Set de elementoIds (number)

        // Clipboard
        this._clipboard = null;

        // Opções
        this.snapAtivo   = true;
        this.guiasAtivas = true;
        this.gradeAtiva  = false;

        // Context menu
        this._ctxMenu = null;

        this._initContextMenu();
        this._initTeclado();
    }

    // -------------------------------------------------------------------------
    // Ativação de uma seção em modo livre
    // -------------------------------------------------------------------------

    /**
     * Chama após renderizar/inserir uma seção com [data-modo-canvas="livre"].
     * Adiciona listeners de drag/resize a todos os elementos da seção.
     */
    ativarSecao(secaoEl) {
        if (!secaoEl) return;
        if (secaoEl.dataset.modoCanvas !== 'livre') return;

        const canvasBox = secaoEl.querySelector('.canvas-livre-box');
        if (!canvasBox) return;

        // Ativa handles em cada elemento
        canvasBox.querySelectorAll('.editor-elemento-wrapper').forEach(el => {
            this._ativarElemento(el, canvasBox);
        });

        // Clique no fundo → desmarcar / iniciar rect-selection
        canvasBox.addEventListener('mousedown', (e) => {
            if (e.target === canvasBox || e.target.classList.contains('canvas-livre-box')) {
                if (!e.shiftKey) this._desmarcarTodos();
                this._iniciarRectSel(e, canvasBox);
            }
        });

        // Context menu na seção
        canvasBox.addEventListener('contextmenu', (e) => this._mostrarContextMenu(e));

        // Resize da seção pela alça inferior
        const resizeSecao = secaoEl.querySelector('.secao-resize-handle');
        if (resizeSecao) {
            this._initResizeSecao(resizeSecao, canvasBox, secaoEl);
        }
    }

    /**
     * Adiciona handles de resize e listeners de drag a um elemento.
     */
    _ativarElemento(el, canvasBox) {
        // Remove handles duplicados
        el.querySelectorAll('.canvas-resize-handle').forEach(h => h.remove());

        // Cria os 8 handles
        const dirs = ['n', 'ne', 'e', 'se', 's', 'sw', 'w', 'nw'];
        dirs.forEach(dir => {
            const h = document.createElement('div');
            h.className = `canvas-resize-handle handle-${dir}`;
            h.dataset.dir = dir;
            el.appendChild(h);

            h.addEventListener('mousedown', (e) => {
                e.preventDefault();
                e.stopPropagation();
                this._iniciarResize(e, el, canvasBox, dir);
            });
        });

        // Drag do elemento
        el.addEventListener('mousedown', (e) => {
            if (e.target.closest('.canvas-resize-handle, .btn-acao-elem, .editor-elemento-toolbar')) return;
            if (e.button !== 0) return;
            e.preventDefault();
            e.stopPropagation();

            const id = parseInt(el.dataset.elementoId, 10);

            if (e.shiftKey) {
                this._toggleSelecao(id, el);
            } else {
                if (!this.selecionados.has(id)) {
                    this._desmarcarTodos();
                    this._selecionar(id, el);
                }
            }

            this._iniciarDrag(e, canvasBox);
        });

        // Double-click → inline edit
        el.addEventListener('dblclick', (e) => {
            if (e.target.closest('.canvas-resize-handle')) return;
            if (this.editor.inlineEditManager) {
                const id = parseInt(el.dataset.elementoId, 10);
                this.editor.inlineEditManager.iniciarEdicao(id, el);
            }
        });

        // Context menu
        el.addEventListener('contextmenu', (e) => {
            e.stopPropagation();
            const id = parseInt(el.dataset.elementoId, 10);
            if (!this.selecionados.has(id)) {
                this._desmarcarTodos();
                this._selecionar(id, el);
            }
            this._mostrarContextMenu(e);
        });
    }

    // -------------------------------------------------------------------------
    // Drag de Elementos
    // -------------------------------------------------------------------------

    _iniciarDrag(e, canvasBox) {
        const ids = [...this.selecionados];
        const snapshots = ids.map(id => {
            const el = canvasBox.querySelector(`.editor-elemento-wrapper[data-elemento-id="${id}"]`);
            if (!el) return null;
            return {
                id, el,
                startLeft: parseFloat(el.dataset.xPct || 0),
                startTop:  parseFloat(el.dataset.yPx  || 0),
            };
        }).filter(Boolean);

        if (snapshots.length === 0) return;

        this._drag = {
            canvasBox, snapshots,
            startX: e.clientX,
            startY: e.clientY,
            canvasW: canvasBox.offsetWidth,
        };

        document.addEventListener('mousemove', this._onDragMove, { passive: false });
        document.addEventListener('mouseup',   this._onDragEnd);
    }

    _onDragMove = (e) => {
        if (!this._drag) return;
        e.preventDefault();

        const { canvasBox, snapshots, startX, startY, canvasW } = this._drag;
        const dx    = e.clientX - startX;
        const dy    = e.clientY - startY;
        const dxPct = (dx / canvasW) * 100;

        snapshots.forEach(({ el, startLeft, startTop }) => {
            const wPct   = parseFloat(el.dataset.wPct || 80);
            let newLeft  = Math.max(0, Math.min(startLeft + dxPct, 100 - wPct));
            let newTop   = Math.max(0, startTop + dy);

            if (this.snapAtivo) {
                const snapped = this._calcularSnap(newLeft, newTop, el, canvasBox, canvasW);
                newLeft = snapped.left;
                newTop  = snapped.top;
            }

            el.style.left = `${newLeft.toFixed(2)}%`;
            el.style.top  = `${newTop.toFixed(0)}px`;
            el.dataset.xPct = newLeft.toFixed(4);
            el.dataset.yPx  = newTop.toFixed(0);
        });
    }

    _onDragEnd = async () => {
        if (!this._drag) return;
        document.removeEventListener('mousemove', this._onDragMove);
        document.removeEventListener('mouseup',   this._onDragEnd);

        for (const { id, el } of this._drag.snapshots) {
            await this._persistirPosicao(id, {
                x_pct:  parseFloat(el.dataset.xPct  || 0),
                y_px:   parseFloat(el.dataset.yPx   || 0),
                w_pct:  parseFloat(el.dataset.wPct  || 80),
                h_auto: el.dataset.hAuto !== 'false',
                h_px:   el.dataset.hAuto !== 'false' ? null : parseFloat(el.dataset.hPx || 0),
            });
        }

        if (this.editor.historicoUndo) this.editor.historicoUndo.snapshot();
        this._drag = null;
    }

    // -------------------------------------------------------------------------
    // Resize de Elementos
    // -------------------------------------------------------------------------

    _iniciarResize(e, el, canvasBox, dir) {
        const rect    = el.getBoundingClientRect();
        const boxRect = canvasBox.getBoundingClientRect();

        this._resize = {
            el, canvasBox, dir,
            startX:    e.clientX,
            startY:    e.clientY,
            startW:    rect.width,
            startH:    rect.height,
            startLeft: rect.left - boxRect.left,
            startTop:  rect.top  - boxRect.top,
            canvasW:   canvasBox.offsetWidth,
        };

        document.addEventListener('mousemove', this._onResizeMove, { passive: false });
        document.addEventListener('mouseup',   this._onResizeEnd);
    }

    _onResizeMove = (e) => {
        if (!this._resize) return;
        e.preventDefault();

        const { el, dir, startX, startY, startW, startH, startLeft, startTop, canvasW } = this._resize;
        const dx = e.clientX - startX;
        const dy = e.clientY - startY;

        let newW = startW, newH = startH, newLeft = startLeft, newTop = startTop;

        if (dir.includes('e'))  newW    = Math.max(MIN_W, startW + dx);
        if (dir.includes('w')) { newW   = Math.max(MIN_W, startW - dx); newLeft = startLeft + startW - newW; }
        if (dir.includes('s'))  newH    = Math.max(MIN_H, startH + dy);
        if (dir.includes('n')) { newH   = Math.max(MIN_H, startH - dy); newTop  = startTop  + startH - newH; }

        const newLeftPct = (newLeft / canvasW) * 100;
        const newWPct    = (newW    / canvasW) * 100;

        el.style.left   = `${Math.max(0, newLeftPct).toFixed(2)}%`;
        el.style.top    = `${Math.max(0, newTop).toFixed(0)}px`;
        el.style.width  = `${newWPct.toFixed(2)}%`;
        el.style.height = `${newH.toFixed(0)}px`;

        el.dataset.xPct  = Math.max(0, newLeftPct).toFixed(4);
        el.dataset.yPx   = Math.max(0, newTop).toFixed(0);
        el.dataset.wPct  = newWPct.toFixed(4);
        el.dataset.hPx   = newH.toFixed(0);
        el.dataset.hAuto = 'false';
    }

    _onResizeEnd = async () => {
        if (!this._resize) return;
        document.removeEventListener('mousemove', this._onResizeMove);
        document.removeEventListener('mouseup',   this._onResizeEnd);

        const { el } = this._resize;
        const id = parseInt(el.dataset.elementoId, 10);

        await this._persistirPosicao(id, {
            x_pct:  parseFloat(el.dataset.xPct || 0),
            y_px:   parseFloat(el.dataset.yPx  || 0),
            w_pct:  parseFloat(el.dataset.wPct || 80),
            h_px:   parseFloat(el.dataset.hPx  || 0),
            h_auto: false,
        });

        if (this.editor.historicoUndo) this.editor.historicoUndo.snapshot();
        this._resize = null;
    }

    // -------------------------------------------------------------------------
    // Resize de Seção (alça inferior)
    // -------------------------------------------------------------------------

    _initResizeSecao(handleEl, canvasBox, secaoEl) {
        let startY, startH;

        handleEl.addEventListener('mousedown', (e) => {
            e.preventDefault();
            startY = e.clientY;
            startH = canvasBox.offsetHeight;

            const onMove = (ev) => {
                const dy = ev.clientY - startY;
                canvasBox.style.minHeight = `${Math.max(200, startH + dy)}px`;
            };

            const onUp = () => {
                document.removeEventListener('mousemove', onMove);
                document.removeEventListener('mouseup', onUp);
                const secaoId = secaoEl.dataset.secaoId;
                if (secaoId) this._persistirAlturaSecao(secaoId, canvasBox.offsetHeight);
            };

            document.addEventListener('mousemove', onMove);
            document.addEventListener('mouseup', onUp);
        });
    }

    // -------------------------------------------------------------------------
    // Seleção por Retângulo
    // -------------------------------------------------------------------------

    _iniciarRectSel(e, canvasBox) {
        const boxRect = canvasBox.getBoundingClientRect();
        const startX  = e.clientX - boxRect.left;
        const startY  = e.clientY - boxRect.top;

        const selBox = document.createElement('div');
        selBox.className = 'canvas-selection-rect';
        selBox.style.cssText = `left:${startX}px; top:${startY}px; width:0; height:0;`;
        canvasBox.appendChild(selBox);

        const onMove = (ev) => {
            const curX = ev.clientX - boxRect.left;
            const curY = ev.clientY - boxRect.top;
            selBox.style.cssText = `
                left:${Math.min(startX, curX)}px;
                top:${Math.min(startY, curY)}px;
                width:${Math.abs(curX - startX)}px;
                height:${Math.abs(curY - startY)}px;
            `;
        };

        const onUp = () => {
            document.removeEventListener('mousemove', onMove);
            document.removeEventListener('mouseup', onUp);
            const selRect = selBox.getBoundingClientRect();
            selBox.remove();

            // Seleciona elementos que intersectam
            canvasBox.querySelectorAll('.editor-elemento-wrapper').forEach(el => {
                const er = el.getBoundingClientRect();
                if (er.left < selRect.right && er.right > selRect.left &&
                    er.top  < selRect.bottom && er.bottom > selRect.top) {
                    this._selecionar(parseInt(el.dataset.elementoId, 10), el);
                }
            });
        };

        document.addEventListener('mousemove', onMove);
        document.addEventListener('mouseup', onUp);
    }

    // -------------------------------------------------------------------------
    // Seleção
    // -------------------------------------------------------------------------

    _selecionar(id, el) {
        this.selecionados.add(id);
        el.classList.add('canvas-selected');
        if (this.selecionados.size > 1) el.classList.add('canvas-multi-selected');

        if (this.selecionados.size === 1) {
            if (this.editor.propriedadesManager) {
                this.editor.propriedadesManager.carregarPropriedades('elemento', id, el);
            }
            if (this.editor.selecaoManager) {
                this.editor.selecaoManager.itemSelecionado = { tipo: 'elemento', id, el };
            }
        }
    }

    _toggleSelecao(id, el) {
        if (this.selecionados.has(id)) {
            this.selecionados.delete(id);
            el.classList.remove('canvas-selected', 'canvas-multi-selected');
        } else {
            this._selecionar(id, el);
        }
    }

    _desmarcarTodos() {
        this.selecionados.clear();
        document.querySelectorAll('.canvas-selected, .canvas-multi-selected').forEach(el => {
            el.classList.remove('canvas-selected', 'canvas-multi-selected');
        });
        if (this.editor.selecaoManager) this.editor.selecaoManager.itemSelecionado = null;
        if (this.editor.propriedadesManager) this.editor.propriedadesManager.limpar();
    }

    // -------------------------------------------------------------------------
    // Smart Guides / Snap
    // -------------------------------------------------------------------------

    _calcularSnap(leftPct, topPx, el, canvasBox, canvasW) {
        const wPct    = parseFloat(el.dataset.wPct || 80);
        const hPx     = el.offsetHeight;
        const leftPx  = (leftPct / 100) * canvasW;
        const rightPx = leftPx + (wPct / 100) * canvasW;
        const cenPx   = (leftPx + rightPx) / 2;
        const botPx   = topPx + hPx;

        let snappedLeft = leftPct;
        let snappedTop  = topPx;

        const guias = this._coletarGuias(el, canvasBox, canvasW);

        for (const g of guias) {
            if (g.axis === 'v') {
                const gPx = (g.pct / 100) * canvasW;
                if (Math.abs(leftPx  - gPx) < SNAP_THRESHOLD) snappedLeft = (gPx / canvasW) * 100;
                if (Math.abs(rightPx - gPx) < SNAP_THRESHOLD) snappedLeft = ((gPx - (wPct / 100) * canvasW) / canvasW) * 100;
                if (Math.abs(cenPx   - gPx) < SNAP_THRESHOLD) snappedLeft = ((gPx - (wPct / 200) * canvasW) / canvasW) * 100;
            }
            if (g.axis === 'h') {
                if (Math.abs(topPx - g.px) < SNAP_THRESHOLD) snappedTop = g.px;
                if (Math.abs(botPx - g.px) < SNAP_THRESHOLD) snappedTop = g.px - hPx;
            }
        }

        return { left: Math.max(0, snappedLeft), top: Math.max(0, snappedTop) };
    }

    _coletarGuias(elAtivo, canvasBox, canvasW) {
        const guias = [
            { axis: 'v', pct: 0 },
            { axis: 'v', pct: 50 },
            { axis: 'v', pct: 100 },
            { axis: 'h', px: 0 },
        ];

        canvasBox.querySelectorAll('.editor-elemento-wrapper').forEach(el => {
            if (el === elAtivo || this.selecionados.has(parseInt(el.dataset.elementoId, 10))) return;
            const xPct = parseFloat(el.dataset.xPct || 0);
            const yPx  = parseFloat(el.dataset.yPx  || 0);
            const wPct = parseFloat(el.dataset.wPct || 80);
            const hPx  = el.offsetHeight;

            guias.push({ axis: 'v', pct: xPct },
                       { axis: 'v', pct: xPct + wPct },
                       { axis: 'v', pct: xPct + wPct / 2 },
                       { axis: 'h', px:  yPx },
                       { axis: 'h', px:  yPx + hPx });
        });

        return guias;
    }

    // -------------------------------------------------------------------------
    // Alinhamento
    // -------------------------------------------------------------------------

    alinhar(tipo) {
        const canvasBox = this._getCanvasBoxAtivo();
        if (!canvasBox || this.selecionados.size < 1) return;

        const ids = [...this.selecionados];
        const els = ids.map(id =>
            canvasBox.querySelector(`.editor-elemento-wrapper[data-elemento-id="${id}"]`)
        ).filter(Boolean);
        const canvasW = canvasBox.offsetWidth;

        switch (tipo) {
            case 'left': {
                const ref = Math.min(...els.map(el => parseFloat(el.dataset.xPct || 0)));
                els.forEach(el => { el.dataset.xPct = ref; el.style.left = `${ref}%`; });
                break;
            }
            case 'center':
                els.forEach(el => {
                    const wPct   = parseFloat(el.dataset.wPct || 80);
                    const newL   = 50 - wPct / 2;
                    el.dataset.xPct = newL; el.style.left = `${newL}%`;
                });
                break;
            case 'right': {
                const ref = Math.max(...els.map(el => parseFloat(el.dataset.xPct || 0) + parseFloat(el.dataset.wPct || 80)));
                els.forEach(el => {
                    const wPct = parseFloat(el.dataset.wPct || 80);
                    const newL = ref - wPct;
                    el.dataset.xPct = newL; el.style.left = `${newL}%`;
                });
                break;
            }
            case 'top': {
                const ref = Math.min(...els.map(el => parseFloat(el.dataset.yPx || 0)));
                els.forEach(el => { el.dataset.yPx = ref; el.style.top = `${ref}px`; });
                break;
            }
            case 'middle': {
                const ref = els.reduce((s, el) => s + parseFloat(el.dataset.yPx || 0) + el.offsetHeight / 2, 0) / els.length;
                els.forEach(el => { const t = ref - el.offsetHeight / 2; el.dataset.yPx = t; el.style.top = `${t}px`; });
                break;
            }
            case 'bottom': {
                const ref = Math.max(...els.map(el => parseFloat(el.dataset.yPx || 0) + el.offsetHeight));
                els.forEach(el => { const t = ref - el.offsetHeight; el.dataset.yPx = t; el.style.top = `${t}px`; });
                break;
            }
        }

        els.forEach(el => {
            const id = parseInt(el.dataset.elementoId, 10);
            this._persistirPosicao(id, {
                x_pct:  parseFloat(el.dataset.xPct || 0),
                y_px:   parseFloat(el.dataset.yPx  || 0),
                w_pct:  parseFloat(el.dataset.wPct || 80),
                h_auto: el.dataset.hAuto !== 'false',
            });
        });
    }

    // -------------------------------------------------------------------------
    // Z-index
    // -------------------------------------------------------------------------

    async alterarZIndex(elementoId, acao) {
        const canvasBox = this._getCanvasBoxAtivo();
        if (!canvasBox) return;
        const el = canvasBox.querySelector(`.editor-elemento-wrapper[data-elemento-id="${elementoId}"]`);
        if (!el) return;

        const todos = [...canvasBox.querySelectorAll('.editor-elemento-wrapper')];
        const idx   = todos.indexOf(el);

        if (acao === 'forward'  && idx < todos.length - 1) todos[idx + 1].insertAdjacentElement('afterend',  el);
        else if (acao === 'backward' && idx > 0)           todos[idx - 1].insertAdjacentElement('beforebegin', el);
        else if (acao === 'front')  canvasBox.appendChild(el);
        else if (acao === 'back')   canvasBox.insertBefore(el, canvasBox.firstChild);

        // Atualiza z-index CSS sequencial
        canvasBox.querySelectorAll('.editor-elemento-wrapper').forEach((elem, i) => {
            elem.style.zIndex = i + 1;
            elem.dataset.zIndex = i + 1;
        });

        const z = parseInt(el.dataset.zIndex, 10);
        try {
            await EditorApi.salvarElemento(this.editor.siteUuid, {
                elemento_id: elementoId,
                estilos: { posicao: { z_index: z } },
            });
        } catch (err) {
            console.error('[CanvasLivre] Erro ao salvar z-index:', err);
        }
    }

    // -------------------------------------------------------------------------
    // Context Menu
    // -------------------------------------------------------------------------

    _initContextMenu() {
        this._ctxMenu = document.createElement('div');
        this._ctxMenu.className = 'canvas-context-menu';
        this._ctxMenu.style.display = 'none';
        this._ctxMenu.innerHTML = `
            <ul>
                <li data-acao="copiar">⎘ Copiar</li>
                <li data-acao="colar">⎗ Colar</li>
                <li data-acao="duplicar">⊕ Duplicar</li>
                <li class="ctx-divider"></li>
                <li data-acao="avançar">↑ Avançar</li>
                <li data-acao="recuar">↓ Recuar</li>
                <li data-acao="frente">⤒ Trazer para Frente</li>
                <li data-acao="fundo">⤓ Enviar para o Fundo</li>
                <li class="ctx-divider"></li>
                <li data-acao="excluir" class="ctx-danger">✕ Excluir</li>
            </ul>
        `;
        document.body.appendChild(this._ctxMenu);

        this._ctxMenu.addEventListener('click', (e) => {
            const li = e.target.closest('li[data-acao]');
            if (!li) return;
            this._executarAcaoContexto(li.dataset.acao);
            this._esconderContextMenu();
        });

        document.addEventListener('click', () => this._esconderContextMenu());
    }

    _mostrarContextMenu(e) {
        e.preventDefault();
        const menu = this._ctxMenu;
        menu.style.display = 'block';
        let x = e.clientX, y = e.clientY;
        if (x + 180 > window.innerWidth)  x = window.innerWidth  - 185;
        if (y + 260 > window.innerHeight) y = window.innerHeight - 265;
        menu.style.left = `${x}px`;
        menu.style.top  = `${y}px`;

        const colarLi = menu.querySelector('[data-acao="colar"]');
        if (colarLi) colarLi.style.opacity = this._clipboard ? '1' : '0.4';
    }

    _esconderContextMenu() {
        if (this._ctxMenu) this._ctxMenu.style.display = 'none';
    }

    async _executarAcaoContexto(acao) {
        const sel = this.editor.selecaoManager?.itemSelecionado;
        const ids = [...this.selecionados];

        switch (acao) {
            case 'copiar':
                if (sel) this._clipboard = { tipo: sel.tipo, id: sel.id };
                break;
            case 'colar':
                if (this._clipboard) await this._colar();
                break;
            case 'duplicar':
                if (sel?.tipo === 'elemento') await this.editor.duplicarElemento(sel.id);
                else if (sel?.tipo === 'secao') await this.editor.duplicarSecao(sel.id);
                break;
            case 'avançar':
                if (sel?.tipo === 'elemento') await this.alterarZIndex(sel.id, 'forward');
                break;
            case 'recuar':
                if (sel?.tipo === 'elemento') await this.alterarZIndex(sel.id, 'backward');
                break;
            case 'frente':
                if (sel?.tipo === 'elemento') await this.alterarZIndex(sel.id, 'front');
                break;
            case 'fundo':
                if (sel?.tipo === 'elemento') await this.alterarZIndex(sel.id, 'back');
                break;
            case 'excluir':
                if (ids.length > 0) {
                    for (const id of ids) await this.editor.excluirElemento(id);
                } else if (sel?.tipo === 'secao') {
                    if (confirm('Excluir esta seção?')) await this.editor.excluirSecao(sel.id);
                }
                break;
        }
    }

    async _colar() {
        if (!this._clipboard) return;
        const { tipo, id } = this._clipboard;
        if (tipo !== 'elemento') return;

        try {
            const resp = await EditorApi.duplicarElemento(this.editor.siteUuid, id);
            const canvasBox = this._getCanvasBoxAtivo();
            if (!canvasBox || !resp.html) return;

            canvasBox.insertAdjacentHTML('beforeend', resp.html);
            const novoEl = canvasBox.querySelector(`.editor-elemento-wrapper[data-elemento-id="${resp.elemento_id}"]`);
            if (novoEl) {
                const x = Math.min(parseFloat(novoEl.dataset.xPct || 5) + 3, 80);
                const y = parseFloat(novoEl.dataset.yPx || 0) + 20;
                novoEl.style.left = `${x}%`;
                novoEl.style.top  = `${y}px`;
                novoEl.dataset.xPct = x;
                novoEl.dataset.yPx  = y;
                this._ativarElemento(novoEl, canvasBox);
                this._desmarcarTodos();
                this._selecionar(resp.elemento_id, novoEl);
                await this._persistirPosicao(resp.elemento_id, {
                    x_pct: x, y_px: y, w_pct: parseFloat(novoEl.dataset.wPct || 80), h_auto: true,
                });
            }
        } catch (err) {
            console.error('[CanvasLivre] Erro ao colar:', err);
        }
    }

    // -------------------------------------------------------------------------
    // Atalhos de Teclado
    // -------------------------------------------------------------------------

    _initTeclado() {
        document.addEventListener('keydown', async (e) => {
            if (['INPUT', 'TEXTAREA', 'SELECT'].includes(e.target.tagName)) return;
            if (e.target.contentEditable === 'true') return;

            const sel = this.editor.selecaoManager?.itemSelecionado;
            const ids = [...this.selecionados];

            // DEL / Backspace
            if ((e.key === 'Delete' || e.key === 'Backspace') && ids.length > 0) {
                e.preventDefault();
                for (const id of ids) await this.editor.excluirElemento(id);
                return;
            }

            // CTRL+D — duplicar
            if (e.ctrlKey && e.key === 'd') {
                e.preventDefault();
                if (sel?.tipo === 'elemento') await this.editor.duplicarElemento(sel.id);
                return;
            }

            // CTRL+C
            if (e.ctrlKey && e.key === 'c') {
                if (sel) this._clipboard = { tipo: sel.tipo, id: sel.id };
                return;
            }

            // CTRL+V
            if (e.ctrlKey && e.key === 'v') {
                e.preventDefault();
                if (this._clipboard) await this._colar();
                return;
            }

            // CTRL+Z — desfazer
            if (e.ctrlKey && !e.shiftKey && e.key === 'z') {
                e.preventDefault();
                if (this.editor.historicoUndo) await this.editor.historicoUndo.desfazer();
                return;
            }

            // CTRL+SHIFT+Z — refazer
            if (e.ctrlKey && e.shiftKey && (e.key === 'z' || e.key === 'Z')) {
                e.preventDefault();
                if (this.editor.historicoUndo) await this.editor.historicoUndo.refazer();
                return;
            }

            // Setas — mover
            if (['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown'].includes(e.key) && ids.length > 0) {
                e.preventDefault();
                const delta   = e.shiftKey ? 10 : 1;
                const canvasBox = this._getCanvasBoxAtivo();
                if (!canvasBox) return;
                const canvasW = canvasBox.offsetWidth;

                for (const id of ids) {
                    const el = canvasBox.querySelector(`.editor-elemento-wrapper[data-elemento-id="${id}"]`);
                    if (!el) continue;
                    let xPct = parseFloat(el.dataset.xPct || 0);
                    let yPx  = parseFloat(el.dataset.yPx  || 0);
                    const dPct = (delta / canvasW) * 100;

                    if (e.key === 'ArrowLeft')  xPct = Math.max(0, xPct - dPct);
                    if (e.key === 'ArrowRight') xPct = xPct + dPct;
                    if (e.key === 'ArrowUp')    yPx  = Math.max(0, yPx - delta);
                    if (e.key === 'ArrowDown')  yPx  = yPx + delta;

                    el.style.left = `${xPct.toFixed(2)}%`;
                    el.style.top  = `${yPx.toFixed(0)}px`;
                    el.dataset.xPct = xPct.toFixed(4);
                    el.dataset.yPx  = yPx.toFixed(0);

                    await this._persistirPosicao(id, {
                        x_pct: xPct, y_px: yPx,
                        w_pct: parseFloat(el.dataset.wPct || 80),
                        h_auto: el.dataset.hAuto !== 'false',
                    });
                }
            }
        });
    }

    // -------------------------------------------------------------------------
    // Utilitários Públicos
    // -------------------------------------------------------------------------

    _getCanvasBoxAtivo() {
        return document.querySelector('.canvas-livre-box') || null;
    }

    async _persistirPosicao(elementoId, posicao) {
        try {
            await EditorApi.salvarElemento(this.editor.siteUuid, {
                elemento_id: elementoId,
                estilos: { posicao },
            });
        } catch (err) {
            console.error('[CanvasLivre] Erro ao persistir posição:', err);
        }
    }

    async _persistirAlturaSecao(secaoId, alturaMinPx) {
        try {
            await EditorApi.salvarSecaoPropriedades(this.editor.siteUuid, secaoId, {
                estilos: { modo_canvas: 'livre', altura_min_px: alturaMinPx },
            });
        } catch (err) {
            console.error('[CanvasLivre] Erro ao salvar altura da seção:', err);
        }
    }

    /**
     * Posiciona um novo elemento recém-criado no canvas livre.
     * Chamado por dragdrop.js após criar o elemento via API.
     * @param {HTMLElement} el
     * @param {HTMLElement} canvasBox
     * @param {number?} dropX - posição X do drop em px relativo ao canvasBox (opcional)
     * @param {number?} dropY - posição Y do drop em px relativo ao canvasBox (opcional)
     * @returns {{ x_pct, y_px, w_pct, h_auto }} — posição aplicada para persistir
     */
    posicionarNovoElemento(el, canvasBox, dropX = null, dropY = null) {
        const canvasW   = canvasBox.offsetWidth;
        const defaultWPct = 80;
        let xPct, yPx;

        if (dropX !== null && dropY !== null) {
            xPct = Math.max(0, Math.min((dropX / canvasW) * 100 - defaultWPct / 2, 100 - defaultWPct));
            yPx  = Math.max(0, dropY - 20);
        } else {
            // Empilha abaixo do último elemento
            xPct = (100 - defaultWPct) / 2;
            yPx  = 20;
            canvasBox.querySelectorAll('.editor-elemento-wrapper').forEach(existing => {
                if (existing === el) return;
                const y = parseFloat(existing.dataset.yPx || 0);
                const h = existing.offsetHeight;
                yPx = Math.max(yPx, y + h + 16);
            });
        }

        el.style.position = 'absolute';
        el.style.left  = `${xPct.toFixed(2)}%`;
        el.style.top   = `${yPx.toFixed(0)}px`;
        el.style.width = `${defaultWPct}%`;

        el.dataset.xPct  = xPct.toFixed(4);
        el.dataset.yPx   = yPx.toFixed(0);
        el.dataset.wPct  = defaultWPct.toFixed(4);
        el.dataset.hAuto = 'true';

        this._ativarElemento(el, canvasBox);
        this._desmarcarTodos();
        this._selecionar(parseInt(el.dataset.elementoId, 10), el);

        return { x_pct: xPct, y_px: yPx, w_pct: defaultWPct, h_auto: true };
    }

    // Toggles
    toggleSnap()  { this.snapAtivo   = !this.snapAtivo; }
    toggleGuias() { this.guiasAtivas = !this.guiasAtivas; }
    toggleGrade() {
        this.gradeAtiva = !this.gradeAtiva;
        document.querySelectorAll('.canvas-livre-box').forEach(box => {
            box.classList.toggle('canvas-grade-ativa', this.gradeAtiva);
        });
    }
}
