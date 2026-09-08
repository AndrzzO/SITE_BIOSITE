/**
 * api.js — Cliente HTTP assíncrono com CSRF e tratamento de erros do Editor
 */

export function getCsrfToken() {
    const cookie = document.cookie
        .split('; ')
        .find(row => row.startsWith('csrftoken='));
    if (cookie) {
        return cookie.split('=')[1];
    }
    const metaTag = document.querySelector('meta[name="csrf-token"]');
    return metaTag ? metaTag.getAttribute('content') : '';
}

export async function fetchJson(url, options = {}) {
    const defaultHeaders = {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCsrfToken(),
        'X-Requested-With': 'XMLHttpRequest'
    };

    const config = {
        ...options,
        headers: {
            ...defaultHeaders,
            ...options.headers
        }
    };

    try {
        const response = await fetch(url, config);
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.erro || `Erro HTTP ${response.status}`);
        }

        return data;
    } catch (err) {
        console.error(`Falha na requisição para ${url}:`, err);
        throw err;
    }
}

export const EditorApi = {
    async obterDados(siteUuid, paginaId = null) {
        const url = `/painel/sites/${siteUuid}/editor/dados/${paginaId ? `?pagina=${paginaId}` : ''}`;
        return fetchJson(url, { method: 'GET' });
    },

    async salvarElemento(siteUuid, payload) {
        return fetchJson(`/painel/sites/${siteUuid}/editor/elemento/salvar/`, {
            method: 'POST',
            body: JSON.stringify(payload)
        });
    },

    async criarElemento(siteUuid, payload) {
        return fetchJson(`/painel/sites/${siteUuid}/editor/elemento/criar/`, {
            method: 'POST',
            body: JSON.stringify(payload)
        });
    },

    async moverElemento(siteUuid, payload) {
        return fetchJson(`/painel/sites/${siteUuid}/editor/elemento/mover/`, {
            method: 'POST',
            body: JSON.stringify(payload)
        });
    },

    async duplicarElemento(siteUuid, elementoId) {
        return fetchJson(`/painel/sites/${siteUuid}/editor/elemento/${elementoId}/duplicar/`, {
            method: 'POST'
        });
    },

    async excluirElemento(siteUuid, elementoId) {
        return fetchJson(`/painel/sites/${siteUuid}/editor/elemento/${elementoId}/excluir/`, {
            method: 'POST'
        });
    },

    async criarSecao(siteUuid, payload) {
        return fetchJson(`/painel/sites/${siteUuid}/editor/secao/criar/`, {
            method: 'POST',
            body: JSON.stringify(payload)
        });
    },

    async moverSecoes(siteUuid, payload) {
        return fetchJson(`/painel/sites/${siteUuid}/editor/secao/mover/`, {
            method: 'POST',
            body: JSON.stringify(payload)
        });
    },

    async duplicarSecao(siteUuid, secaoId) {
        return fetchJson(`/painel/sites/${siteUuid}/editor/secao/${secaoId}/duplicar/`, {
            method: 'POST'
        });
    },

    async excluirSecao(siteUuid, secaoId) {
        return fetchJson(`/painel/sites/${siteUuid}/editor/secao/${secaoId}/excluir/`, {
            method: 'POST'
        });
    },

    async salvarSecaoPropriedades(siteUuid, secaoId, payload) {
        return fetchJson(`/painel/sites/${siteUuid}/editor/secao/${secaoId}/propriedades/`, {
            method: 'POST',
            body: JSON.stringify(payload)
        });
    },

    async listarBlocos(siteUuid) {
        return fetchJson(`/painel/sites/${siteUuid}/editor/blocos/listar/`, {
            method: 'GET'
        });
    },

    async inserirBloco(siteUuid, payload) {
        return fetchJson(`/painel/sites/${siteUuid}/editor/bloco/inserir/`, {
            method: 'POST',
            body: JSON.stringify(payload)
        });
    },

    async salvarSecaoComoBloco(siteUuid, secaoId, payload) {
        return fetchJson(`/painel/sites/${siteUuid}/editor/secao/${secaoId}/salvar-bloco/`, {
            method: 'POST',
            body: JSON.stringify(payload)
        });
    },

    async salvarProjetoComoTemplate(siteUuid, payload) {
        return fetchJson(`/painel/sites/${siteUuid}/salvar-template/`, {
            method: 'POST',
            body: JSON.stringify(payload)
        });
    }
};
