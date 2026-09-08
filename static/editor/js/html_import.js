/**
 * html_import.js — Importador de HTML externo para o Canvas Livre
 *
 * Suporta dois modos:
 * 1. Modo Nativo: Converte tags reconhecidas (h1-h6, p, img, a/button, hr) em elementos BioSite
 * 2. Modo Sandbox: Preserva o HTML original isolado em um iframe sandboxed (HTML_EMBED)
 */

import { EditorApi } from './api.js';

export class HtmlImportManager {
    constructor(editor) {
        this.editor = editor;
        this.modalEl = document.getElementById('modal-import-html');
        this.textareaEl = document.getElementById('import-html-codigo');
        this.previewIframe = document.getElementById('import-html-preview-frame');
        this.btnConfirmar = document.getElementById('btn-confirmar-importacao-html');
        this.radioModoNativo = document.getElementById('modo-import-nativo');
        this.radioModoSandbox = document.getElementById('modo-import-sandbox');

        this.init();
    }

    init() {
        // Botão para abrir modal
        const btnAbrir = document.getElementById('btn-abrir-import-html');
        if (btnAbrir) {
            btnAbrir.addEventListener('click', () => this.abrirModal());
        }

        // Preview em tempo real ao digitar
        if (this.textareaEl) {
            this.textareaEl.addEventListener('input', () => this.atualizarPreview());
        }

        // Confirmação
        if (this.btnConfirmar) {
            this.btnConfirmar.addEventListener('click', () => this.executarImportacao());
        }

        // Fechar modal
        if (this.modalEl) {
            this.modalEl.querySelectorAll('[data-fechar-modal]').forEach(b => {
                b.addEventListener('click', () => this.fecharModal());
            });
        }
    }

    abrirModal() {
        if (!this.modalEl) return;
        this.modalEl.style.display = 'flex';
        if (this.textareaEl) {
            this.textareaEl.focus();
            this.atualizarPreview();
        }
    }

    fecharModal() {
        if (!this.modalEl) return;
        this.modalEl.style.display = 'none';
    }

    atualizarPreview() {
        if (!this.previewIframe || !this.textareaEl) return;
        const codigo = this.textareaEl.value.trim();
        const doc = `<!DOCTYPE html><html><head><meta charset="utf-8"><style>body{margin:0;padding:12px;font-family:sans-serif;color:#111;}</style></head><body>${codigo}</body></html>`;
        this.previewIframe.srcdoc = doc;
    }

    async executarImportacao() {
        const codigo = this.textareaEl?.value.trim();
        if (!codigo) {
            alert('Por favor, cole o código HTML a ser importado.');
            return;
        }

        const ehNativo = this.radioModoNativo?.checked ?? true;
        const secaoAtiva = this._obterSecaoAtiva();

        if (!secaoAtiva) {
            alert('Nenhuma seção encontrada. Adicione uma seção antes de importar.');
            return;
        }

        const containerId = secaoAtiva.querySelector('[data-container-id]')?.dataset.containerId;
        if (!containerId) {
            alert('Container da seção não encontrado.');
            return;
        }

        this.editor.mostrarStatusSalvando();
        this.fecharModal();

        try {
            if (!ehNativo) {
                // Modo Sandbox: cria elemento HTML_EMBED
                await this._importarComoEmbed(containerId, secaoAtiva, codigo);
            } else {
                // Modo Nativo: converte tags para elementos nativos
                await this._importarComoElementosNativos(containerId, secaoAtiva, codigo);
            }

            if (this.editor.historicoUndo) this.editor.historicoUndo.snapshot();
            this.editor.mostrarStatusSalvo();
        } catch (err) {
            console.error('[HtmlImport] Erro durante importação:', err);
            this.editor.mostrarStatusErro(err.message);
        }
    }

    async _importarComoEmbed(containerId, secaoAtiva, codigoHtml) {
        const resp = await EditorApi.criarElemento(this.editor.siteUuid, {
            container_id: containerId,
            tipo: 'HTML_EMBED'
        });

        if (resp.elemento_id) {
            // Salva o código HTML dentro do conteúdo
            await EditorApi.salvarElemento(this.editor.siteUuid, {
                elemento_id: resp.elemento_id,
                conteudo: {
                    codigo_html: codigoHtml,
                    altura_px: 200
                }
            });

            // Insere no DOM
            this._inserirNoCanvas(secaoAtiva, resp.html, resp.elemento_id);
        }
    }

    async _importarComoElementosNativos(containerId, secaoAtiva, codigoHtml) {
        const parser = new DOMParser();
        const doc = parser.parseFromString(codigoHtml, 'text/html');
        const nos = Array.from(doc.body.children);

        if (nos.length === 0 && doc.body.textContent.trim()) {
            // Texto puro solto
            await this._criarElementoTexto(containerId, secaoAtiva, doc.body.textContent.trim());
            return;
        }

        for (const no of nos) {
            const tag = no.tagName.toLowerCase();

            if (['h1', 'h2', 'h3', 'h4', 'h5', 'h6'].includes(tag)) {
                await this._criarElementoTitulo(containerId, secaoAtiva, no.textContent.trim(), tag);
            } else if (tag === 'p' || tag === 'span' || tag === 'div' && no.children.length === 0) {
                const txt = no.textContent.trim();
                if (txt) await this._criarElementoTexto(containerId, secaoAtiva, txt);
            } else if (tag === 'img') {
                const src = no.getAttribute('src');
                const alt = no.getAttribute('alt') || '';
                if (src) await this._criarElementoImagem(containerId, secaoAtiva, src, alt);
            } else if (tag === 'a' || tag === 'button') {
                const label = no.textContent.trim() || 'Clique Aqui';
                const url = no.getAttribute('href') || '#';
                await this._criarElementoBotao(containerId, secaoAtiva, label, url);
            } else if (tag === 'hr') {
                await this._criarElementoSimples(containerId, secaoAtiva, 'DIVISOR');
            } else {
                // Conteúdo complexo preservado em sandbox embed
                await this._importarComoEmbed(containerId, secaoAtiva, no.outerHTML);
            }
        }
    }

    async _criarElementoTitulo(containerId, secaoAtiva, texto, nivel) {
        const resp = await EditorApi.criarElemento(this.editor.siteUuid, {
            container_id: containerId,
            tipo: 'TITULO'
        });
        if (resp.elemento_id) {
            await EditorApi.salvarElemento(this.editor.siteUuid, {
                elemento_id: resp.elemento_id,
                conteudo: { texto, nivel }
            });
            this._inserirNoCanvas(secaoAtiva, resp.html, resp.elemento_id);
        }
    }

    async _criarElementoTexto(containerId, secaoAtiva, texto) {
        const resp = await EditorApi.criarElemento(this.editor.siteUuid, {
            container_id: containerId,
            tipo: 'TEXTO'
        });
        if (resp.elemento_id) {
            await EditorApi.salvarElemento(this.editor.siteUuid, {
                elemento_id: resp.elemento_id,
                conteudo: { texto }
            });
            this._inserirNoCanvas(secaoAtiva, resp.html, resp.elemento_id);
        }
    }

    async _criarElementoImagem(containerId, secaoAtiva, url, alt) {
        const resp = await EditorApi.criarElemento(this.editor.siteUuid, {
            container_id: containerId,
            tipo: 'IMAGEM'
        });
        if (resp.elemento_id) {
            await EditorApi.salvarElemento(this.editor.siteUuid, {
                elemento_id: resp.elemento_id,
                conteudo: { url_imagem: url, texto_alternativo: alt }
            });
            this._inserirNoCanvas(secaoAtiva, resp.html, resp.elemento_id);
        }
    }

    async _criarElementoBotao(containerId, secaoAtiva, rotulo, url) {
        const resp = await EditorApi.criarElemento(this.editor.siteUuid, {
            container_id: containerId,
            tipo: 'BOTAO'
        });
        if (resp.elemento_id) {
            await EditorApi.salvarElemento(this.editor.siteUuid, {
                elemento_id: resp.elemento_id,
                conteudo: { rotulo, url }
            });
            this._inserirNoCanvas(secaoAtiva, resp.html, resp.elemento_id);
        }
    }

    async _criarElementoSimples(containerId, secaoAtiva, tipo) {
        const resp = await EditorApi.criarElemento(this.editor.siteUuid, {
            container_id: containerId,
            tipo
        });
        if (resp.elemento_id) {
            this._inserirNoCanvas(secaoAtiva, resp.html, resp.elemento_id);
        }
    }

    _inserirNoCanvas(secaoAtiva, html, elementoId) {
        const canvasBox = secaoAtiva.querySelector('.canvas-livre-box');
        if (canvasBox && this.editor.canvasLivreManager) {
            canvasBox.insertAdjacentHTML('beforeend', html);
            const novoEl = canvasBox.querySelector(`.editor-elemento-wrapper[data-elemento-id="${elementoId}"]`);
            if (novoEl) {
                const pos = this.editor.canvasLivreManager.posicionarNovoElemento(novoEl, canvasBox);
                this.editor.canvasLivreManager._persistirPosicao(elementoId, pos);
            }
        } else {
            // Modo fluxo
            const dropzone = secaoAtiva.querySelector('.sortable-container-elementos');
            if (dropzone) {
                dropzone.insertAdjacentHTML('beforeend', html);
            }
        }
    }

    _obterSecaoAtiva() {
        const sel = this.editor.selecaoManager?.itemSelecionado;
        if (sel?.el) {
            const s = sel.el.closest('.editor-secao-wrapper');
            if (s) return s;
        }
        return document.querySelector('.editor-secao-wrapper');
    }
}
