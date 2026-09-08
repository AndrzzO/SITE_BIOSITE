/**
 * autosave.js — Fila de Salvamento com Debounce e Indicadores de Estado
 */

import { EditorApi } from './api.js';

export class AutosaveManager {
    constructor(editor, debounceMs = 700) {
        this.editor = editor;
        this.debounceMs = debounceMs;
        this.timer = null;
        this.filaMudancas = {};
        this.pendente = false;

        this.statusEl = document.getElementById('autosave-indicador');
        this.initBeforeUnload();
    }

    initBeforeUnload() {
        window.addEventListener('beforeunload', (e) => {
            if (this.pendente) {
                e.preventDefault();
                e.returnValue = 'Existem alterações não salvas no rascunho. Deseja realmente sair?';
                return e.returnValue;
            }
        });
    }

    agendarSalvamento(payload) {
        this.pendente = true;
        this.definirStatus('salvando');

        // Mescla alterações pelo elemento_id
        if (payload.elemento_id) {
            const id = payload.elemento_id;
            if (!this.filaMudancas[id]) {
                this.filaMudancas[id] = { elemento_id: id };
            }
            if (payload.conteudo) {
                this.filaMudancas[id].conteudo = {
                    ...(this.filaMudancas[id].conteudo || {}),
                    ...payload.conteudo
                };
            }
            if (payload.estilos) {
                this.filaMudancas[id].estilos = {
                    ...(this.filaMudancas[id].estilos || {}),
                    ...payload.estilos
                };
            }
        }

        clearTimeout(this.timer);
        this.timer = setTimeout(() => {
            this.processarFila();
        }, this.debounceMs);
    }

    async processarFila() {
        if (!this.pendente) return;

        const itens = Object.values(this.filaMudancas);
        this.filaMudancas = {};

        try {
            for (const item of itens) {
                await EditorApi.salvarElemento(this.editor.siteUuid, item);
            }
            this.pendente = false;
            this.definirStatus('salvo');
        } catch (err) {
            console.error('[Autosave] Erro ao persistir alterações:', err);
            this.definirStatus('erro');
        }
    }

    definirStatus(estado) {
        if (!this.statusEl) return;

        this.statusEl.className = `autosave-status ${estado}`;
        const textoEl = this.statusEl.querySelector('.autosave-texto');

        if (textoEl) {
            if (estado === 'salvando') {
                textoEl.textContent = 'Salvando...';
            } else if (estado === 'salvo') {
                textoEl.textContent = '✓ Salvo';
            } else if (estado === 'erro') {
                textoEl.textContent = 'Erro ao salvar';
            }
        }
    }
}
