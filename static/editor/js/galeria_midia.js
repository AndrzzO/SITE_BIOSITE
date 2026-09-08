/**
 * galeria_midia.js — Gerenciador da Galeria de Mídias e Upload de Imagens do PC
 */

import { EditorApi } from './api.js';

export class GaleriaMidiaManager {
    constructor(editor) {
        this.editor = editor;
        this.modalEl = document.getElementById('modal-galeria-midia');
        this.gridEl = document.getElementById('grid-galeria-midias');
        this.inputUpload = document.getElementById('input-galeria-upload-file');
        this.btnUploadModal = document.getElementById('btn-galeria-novo-upload');
        this.onSelectCallback = null;

        this.init();
    }

    init() {
        if (!this.modalEl) return;

        // Botões de fechar modal
        this.modalEl.querySelectorAll('[data-fechar-modal]').forEach(btn => {
            btn.addEventListener('click', () => this.fechar());
        });

        // Botão de upload dentro do modal
        if (this.btnUploadModal && this.inputUpload) {
            this.btnUploadModal.addEventListener('click', () => {
                this.inputUpload.click();
            });

            this.inputUpload.addEventListener('change', async (e) => {
                const file = e.target.files?.[0];
                if (!file) return;
                await this.fazerUpload(file);
                this.inputUpload.value = '';
            });
        }
    }

    abrir(onSelectCallback) {
        this.onSelectCallback = onSelectCallback;
        if (!this.modalEl) return;
        this.modalEl.style.display = 'flex';
        this.carregarMidias();
    }

    fechar() {
        if (!this.modalEl) return;
        this.modalEl.style.display = 'none';
        this.onSelectCallback = null;
    }

    async carregarMidias() {
        if (!this.gridEl) return;
        this.gridEl.innerHTML = `
            <div style="grid-column: 1/-1; text-align: center; color: var(--studio-text-muted); padding: 2rem 0;">
                Carregando mídias do projeto...
            </div>
        `;

        try {
            const data = await EditorApi.listarMidias(this.editor.siteUuid);
            const midias = data.midias || [];

            if (midias.length === 0) {
                this.gridEl.innerHTML = `
                    <div style="grid-column: 1/-1; text-align: center; color: var(--studio-text-muted); padding: 2rem 0;">
                        Nenhuma imagem enviada ainda. Clique em "Escolher Imagem do PC" para enviar sua primeira foto.
                    </div>
                `;
                return;
            }

            this.gridEl.innerHTML = midias.map(m => `
                <div class="galeria-card-item" data-url="${m.url}" title="${m.nome} (${m.largura}x${m.altura})">
                    <div class="galeria-thumb-wrapper">
                        <img src="${m.url}" alt="${m.nome}" loading="lazy">
                    </div>
                    <div class="galeria-item-nome">${m.nome}</div>
                </div>
            `).join('');

            // Ao clicar em uma imagem da galeria, seleciona e chama o callback
            this.gridEl.querySelectorAll('.galeria-card-item').forEach(card => {
                card.addEventListener('click', () => {
                    const url = card.dataset.url;
                    if (this.onSelectCallback) {
                        this.onSelectCallback(url);
                    }
                    this.fechar();
                });
            });
        } catch (err) {
            this.gridEl.innerHTML = `
                <div style="grid-column: 1/-1; text-align: center; color: #ef4444; padding: 2rem 0;">
                    Erro ao carregar mídias: ${err.message}
                </div>
            `;
        }
    }

    async fazerUpload(file, tipo = 'IMAGEM') {
        const btnUpload = this.btnUploadModal;
        const textoOriginal = btnUpload ? btnUpload.innerHTML : '';
        if (btnUpload) {
            btnUpload.disabled = true;
            btnUpload.innerHTML = '⏳ Enviando...';
        }

        try {
            this.editor.mostrarStatusSalvando();
            const resp = await EditorApi.uploadMidia(this.editor.siteUuid, file, tipo);
            this.editor.mostrarStatusSalvo();

            // Recarrega a galeria
            await this.carregarMidias();

            // Se o usuário já estava esperando para aplicar a imagem, aplica direto
            if (this.onSelectCallback && resp.midia?.url) {
                this.onSelectCallback(resp.midia.url);
                this.fechar();
            }

            return resp.midia?.url;
        } catch (err) {
            this.editor.mostrarStatusErro(err.message);
            alert(`Falha ao enviar imagem: ${err.message}`);
            return null;
        } finally {
            if (btnUpload) {
                btnUpload.disabled = false;
                btnUpload.innerHTML = textoOriginal;
            }
        }
    }
}
