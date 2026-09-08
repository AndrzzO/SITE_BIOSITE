/**
 * canvas.js — Gestão de Viewports Mobile-First, Zoom e Moldura do Smartphone
 */

export class CanvasManager {
    constructor() {
        this.viewportEl = document.getElementById('studio-canvas-viewport');
        this.mockupEl = document.getElementById('phone-mockup-wrapper');
        this.zoomEl = document.getElementById('zoom-indicador');
        this.larguraAtual = 390; // Default Mobile-First
        this.zoomAtual = 1.0;

        this.initEventListeners();
    }

    initEventListeners() {
        // Botões de Viewport na Barra Inferior
        document.querySelectorAll('.btn-viewport').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const largura = e.currentTarget.dataset.viewport;
                this.definirViewport(largura);
            });
        });

        // Controles de Zoom
        const btnZoomIn = document.getElementById('btn-zoom-in');
        const btnZoomOut = document.getElementById('btn-zoom-out');
        const btnZoomReset = document.getElementById('btn-zoom-reset');

        if (btnZoomIn) {
            btnZoomIn.addEventListener('click', () => this.alterarZoom(0.1));
        }
        if (btnZoomOut) {
            btnZoomOut.addEventListener('click', () => this.alterarZoom(-0.1));
        }
        if (btnZoomReset) {
            btnZoomReset.addEventListener('click', () => this.definirZoom(1.0));
        }

        // Toggle Moldura Smartphone / Modo Limpo
        const btnToggleFrame = document.getElementById('btn-toggle-frame');
        if (btnToggleFrame) {
            btnToggleFrame.addEventListener('click', () => this.alternarMoldura());
        }
    }

    definirViewport(largura) {
        if (!this.viewportEl) return;

        document.querySelectorAll('.btn-viewport').forEach(b => b.classList.remove('active'));
        const btnAtivo = document.querySelector(`.btn-viewport[data-viewport="${largura}"]`);
        if (btnAtivo) btnAtivo.classList.add('active');

        if (largura === 'desktop') {
            this.viewportEl.style.width = '100%';
            this.viewportEl.style.maxWidth = '1024px';
            if (this.mockupEl) this.mockupEl.classList.add('clean-mode');
        } else {
            const px = parseInt(largura, 10);
            this.larguraAtual = px;
            this.viewportEl.style.width = `${px}px`;
            this.viewportEl.style.maxWidth = `${px}px`;
            if (this.mockupEl) this.mockupEl.classList.remove('clean-mode');
        }

        this.verificarOverflow();
    }

    alterarZoom(delta) {
        const novoZoom = Math.min(Math.max(this.zoomAtual + delta, 0.6), 1.5);
        this.definirZoom(novoZoom);
    }

    definirZoom(zoom) {
        this.zoomAtual = Math.round(zoom * 10) / 10;
        if (this.viewportEl) {
            this.viewportEl.style.transform = `scale(${this.zoomAtual})`;
        }
        if (this.zoomEl) {
            this.zoomEl.textContent = `${Math.round(this.zoomAtual * 100)}%`;
        }
    }

    alternarMoldura() {
        if (!this.mockupEl) return;
        this.mockupEl.classList.toggle('clean-mode');
    }

    verificarOverflow() {
        // Alerta visual discreto caso algum elemento force scroll horizontal
        const root = document.getElementById('biosite-canvas-root');
        if (!root) return;
        if (root.scrollWidth > root.clientWidth) {
            console.warn('[Canvas] Overflow horizontal detectado em largura:', this.larguraAtual);
        }
    }
}
