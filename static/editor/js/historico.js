/**
 * historico.js — Pilha de Desfazer/Refazer na Sessão e Atalhos de Teclado
 */

export class HistoricoManager {
    constructor(editor, maxOperacoes = 50) {
        this.editor = editor;
        this.maxOperacoes = maxOperacoes;
        this.pilhaDesfazer = [];
        this.pilhaRefazer = [];

        this.initShortcuts();
    }

    initShortcuts() {
        window.addEventListener('keydown', (e) => {
            const tagAtiva = document.activeElement ? document.activeElement.tagName.toLowerCase() : '';
            const isInputOuContentEditable =
                tagAtiva === 'input' ||
                tagAtiva === 'textarea' ||
                tagAtiva === 'select' ||
                document.activeElement?.isContentEditable;

            // Ctrl+S: Forçar salvamento do rascunho
            if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 's') {
                e.preventDefault();
                if (this.editor.autosaveManager) {
                    this.editor.autosaveManager.processarFila();
                }
                return;
            }

            // Ctrl+Z: Desfazer
            if ((e.ctrlKey || e.metaKey) && !e.shiftKey && e.key.toLowerCase() === 'z') {
                if (!isInputOuContentEditable) {
                    e.preventDefault();
                    this.desfazer();
                }
                return;
            }

            // Ctrl+Y ou Ctrl+Shift+Z: Refazer
            if (
                ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'y') ||
                ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key.toLowerCase() === 'z')
            ) {
                if (!isInputOuContentEditable) {
                    e.preventDefault();
                    this.refazer();
                }
                return;
            }

            // Ctrl+D: Duplicar selecionado
            if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'd') {
                if (!isInputOuContentEditable) {
                    e.preventDefault();
                    this.editor.duplicarSelecionado();
                }
                return;
            }

            // Delete / Backspace: Excluir selecionado
            if (e.key === 'Delete' || e.key === 'Backspace') {
                if (!isInputOuContentEditable) {
                    e.preventDefault();
                    this.editor.excluirSelecionado();
                }
                return;
            }

            // Escape: Desmarcar seleção
            if (e.key === 'Escape') {
                this.editor.selecaoManager?.desmarcar();
            }
        });

        // Botões na Barra Inferior
        document.getElementById('btn-desfazer')?.addEventListener('click', () => this.desfazer());
        document.getElementById('btn-refazer')?.addEventListener('click', () => this.refazer());
    }

    registrarAcao(descricao, dados) {
        this.pilhaDesfazer.push({ descricao, ...dados });
        if (this.pilhaDesfazer.length > this.maxOperacoes) {
            this.pilhaDesfazer.shift();
        }
        this.pilhaRefazer = []; // Nova ação limpa refazer
        this.atualizarBotoes();
    }

    async desfazer() {
        if (this.pilhaDesfazer.length === 0) return;
        const acao = this.pilhaDesfazer.pop();
        this.pilhaRefazer.push(acao);

        // Aplica estado anterior
        if (acao.tipo === 'elemento' && acao.anterior) {
            await this.editor.autosaveManager.agendarSalvamento({
                elemento_id: acao.id,
                conteudo: acao.anterior.conteudo,
                estilos: acao.anterior.estilos
            });
            // Recarrega visualização
            this.editor.recarregarPaginaAtiva();
        }

        this.atualizarBotoes();
    }

    async refazer() {
        if (this.pilhaRefazer.length === 0) return;
        const acao = this.pilhaRefazer.pop();
        this.pilhaDesfazer.push(acao);

        // Aplica estado novo
        if (acao.tipo === 'elemento' && acao.novo) {
            await this.editor.autosaveManager.agendarSalvamento({
                elemento_id: acao.id,
                conteudo: acao.novo.conteudo,
                estilos: acao.novo.estilos
            });
            this.editor.recarregarPaginaAtiva();
        }

        this.atualizarBotoes();
    }

    atualizarBotoes() {
        const btnDesfazer = document.getElementById('btn-desfazer');
        const btnRefazer = document.getElementById('btn-refazer');
        if (btnDesfazer) btnDesfazer.disabled = this.pilhaDesfazer.length === 0;
        if (btnRefazer) btnRefazer.disabled = this.pilhaRefazer.length === 0;
    }
}
