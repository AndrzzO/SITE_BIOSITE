/**
 * historico_undo.js — Pilha de Undo/Redo Local (CTRL+Z / CTRL+SHIFT+Z)
 *
 * Estratégia: snapshot das posições e estilos de todos os elementos visíveis
 * no canvas. Armazena até MAX_ESTADOS estados em memória. Não faz request
 * no mousemove — persiste ao servidor apenas ao aplicar undo/redo.
 */

import { EditorApi } from './api.js';

const MAX_ESTADOS = 50;

export class HistoricoUndoManager {
    constructor(editor) {
        this.editor = editor;
        this._pilha   = [];  // estados anteriores
        this._futura  = [];  // estados desfeitos (para refazer)
        this._salvando = false;

        // Snapshot inicial após o DOM carregar
        requestAnimationFrame(() => this.snapshot());

        // Atualiza botões
        this._atualizarBotoes();
    }

    // -------------------------------------------------------------------------
    // Snapshot
    // -------------------------------------------------------------------------

    /**
     * Captura o estado atual de todos os elementos do canvas livre.
     * Deve ser chamado após qualquer operação significativa:
     *   - fim do drag (_onDragEnd)
     *   - fim do resize (_onResizeEnd)
     *   - criação de elemento
     *   - exclusão de elemento
     *   - duplicação de elemento
     */
    snapshot() {
        const estado = this._capturarEstado();
        if (!estado) return;

        // Evita snapshot duplicado igual ao último
        const ultimo = this._pilha[this._pilha.length - 1];
        if (ultimo && JSON.stringify(ultimo) === JSON.stringify(estado)) return;

        this._pilha.push(estado);
        if (this._pilha.length > MAX_ESTADOS) this._pilha.shift();

        // Limpa fila de refazer — nova ação invalida refazer anterior
        this._futura = [];

        this._atualizarBotoes();
    }

    // -------------------------------------------------------------------------
    // Desfazer (CTRL+Z)
    // -------------------------------------------------------------------------

    async desfazer() {
        if (this._pilha.length <= 1 || this._salvando) return;

        // Move estado atual para futura
        const estadoAtual = this._pilha.pop();
        this._futura.push(estadoAtual);

        // Aplica o estado anterior
        const estadoAnterior = this._pilha[this._pilha.length - 1];
        if (estadoAnterior) await this._aplicarEstado(estadoAnterior);

        this._atualizarBotoes();
        this.editor.mostrarStatusSalvo();
    }

    // -------------------------------------------------------------------------
    // Refazer (CTRL+SHIFT+Z)
    // -------------------------------------------------------------------------

    async refazer() {
        if (this._futura.length === 0 || this._salvando) return;

        const proximo = this._futura.pop();
        this._pilha.push(proximo);
        await this._aplicarEstado(proximo);

        this._atualizarBotoes();
        this.editor.mostrarStatusSalvo();
    }

    // -------------------------------------------------------------------------
    // Interno — Captura
    // -------------------------------------------------------------------------

    _capturarEstado() {
        const elementos = [];

        document.querySelectorAll('.editor-elemento-wrapper').forEach(el => {
            const id = el.dataset.elementoId;
            if (!id) return;

            elementos.push({
                id:      parseInt(id, 10),
                xPct:    parseFloat(el.dataset.xPct  || 0),
                yPx:     parseFloat(el.dataset.yPx   || 0),
                wPct:    parseFloat(el.dataset.wPct  || 80),
                hPx:     parseFloat(el.dataset.hPx   || 0),
                hAuto:   el.dataset.hAuto !== 'false',
                zIndex:  parseInt(el.dataset.zIndex  || 1, 10),
                visible: el.style.display !== 'none',
            });
        });

        if (elementos.length === 0) return null;
        return { elementos, ts: Date.now() };
    }

    // -------------------------------------------------------------------------
    // Interno — Aplicar estado
    // -------------------------------------------------------------------------

    async _aplicarEstado(estado) {
        if (!estado?.elementos) return;
        this._salvando = true;
        this.editor.mostrarStatusSalvando();

        try {
            for (const snap of estado.elementos) {
                const el = document.querySelector(`.editor-elemento-wrapper[data-elemento-id="${snap.id}"]`);
                if (!el) continue;

                el.style.position = 'absolute';
                el.style.left     = `${snap.xPct.toFixed(2)}%`;
                el.style.top      = `${snap.yPx.toFixed(0)}px`;
                el.style.width    = `${snap.wPct.toFixed(2)}%`;
                el.style.zIndex   = snap.zIndex;

                if (!snap.hAuto) {
                    el.style.height = `${snap.hPx.toFixed(0)}px`;
                } else {
                    el.style.height = '';
                }

                el.dataset.xPct   = snap.xPct.toFixed(4);
                el.dataset.yPx    = snap.yPx.toFixed(0);
                el.dataset.wPct   = snap.wPct.toFixed(4);
                el.dataset.hPx    = snap.hPx.toFixed(0);
                el.dataset.hAuto  = snap.hAuto ? 'true' : 'false';
                el.dataset.zIndex = snap.zIndex;

                // Persiste no servidor
                await EditorApi.salvarElemento(this.editor.siteUuid, {
                    elemento_id: snap.id,
                    estilos: {
                        posicao: {
                            x_pct:   snap.xPct,
                            y_px:    snap.yPx,
                            w_pct:   snap.wPct,
                            h_px:    snap.hAuto ? null : snap.hPx,
                            h_auto:  snap.hAuto,
                            z_index: snap.zIndex,
                        },
                    },
                });
            }
        } catch (err) {
            console.error('[HistoricoUndo] Erro ao aplicar estado:', err);
        } finally {
            this._salvando = false;
        }
    }

    // -------------------------------------------------------------------------
    // Atualizar botões UI
    // -------------------------------------------------------------------------

    _atualizarBotoes() {
        const btnDesfazer = document.getElementById('btn-desfazer');
        const btnRefazer  = document.getElementById('btn-refazer');

        if (btnDesfazer) btnDesfazer.disabled = this._pilha.length <= 1;
        if (btnRefazer)  btnRefazer.disabled  = this._futura.length === 0;
    }
}
