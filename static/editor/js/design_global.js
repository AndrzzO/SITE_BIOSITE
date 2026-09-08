/**
 * Gerenciador do Design System Global e Presets Visuais (Prompt 6).
 *
 * Atualiza CSS Custom Properties instantaneamente no canvas sem recarregar
 * a página e persiste alterações via autosave debounced.
 */

window.BioSiteDesignGlobal = (function () {
    let siteUuid = null;
    let configAtual = {};
    let debounceTimer = null;

    function calcularLuminancia(hex) {
        if (!hex) return 0.5;
        let c = hex.replace('#', '');
        if (c.length === 3) c = c.split('').map(x => x + x).join('');
        if (c.length !== 6) return 0.5;
        const r = parseInt(c.substr(0, 2), 16) / 255;
        const g = parseInt(c.substr(2, 2), 16) / 255;
        const b = parseInt(c.substr(4, 2), 16) / 255;
        const a = [r, g, b].map(v => (v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4)));
        return 0.2126 * a[0] + 0.7152 * a[1] + 0.0722 * a[2];
    }

    function calcularContraste(corTexto, corFundo) {
        const l1 = calcularLuminancia(corTexto);
        const l2 = calcularLuminancia(corFundo);
        const clara = Math.max(l1, l2);
        const escura = Math.min(l1, l2);
        return (clara + 0.05) / (escura + 0.05);
    }

    function atualizarBadgeContraste() {
        const corTexto = document.getElementById('input-cor-texto')?.value || '#0f172a';
        const corFundo = document.getElementById('input-cor-fundo')?.value || '#ffffff';
        const badge = document.getElementById('design-contraste-badge');
        if (!badge) return;

        const ratio = calcularContraste(corTexto, corFundo);
        const formatado = ratio.toFixed(2);

        if (ratio >= 4.5) {
            badge.className = 'design-contrast-badge ok';
            badge.innerHTML = `✓ Contraste Excelente (${formatado}:1)`;
        } else if (ratio >= 3.0) {
            badge.className = 'design-contrast-badge ok';
            badge.innerHTML = `✓ Contraste Razoável (${formatado}:1)`;
        } else {
            badge.className = 'design-contrast-badge alerta';
            badge.innerHTML = `⚠️ Contraste Baixo (${formatado}:1) — Risco de Ilegibilidade`;
        }
    }

    function aplicarTokensNoCanvas(tokens) {
        const root = document.querySelector('.biosite-canvas-root');
        if (!root || !tokens) return;

        for (const [prop, valor] of Object.entries(tokens)) {
            root.style.setProperty(prop, valor);
        }
    }

    function dispararSalvar() {
        if (!siteUuid) return;
        if (debounceTimer) clearTimeout(debounceTimer);

        debounceTimer = setTimeout(async () => {
            const payload = {
                cor_primaria: document.getElementById('input-cor-primaria')?.value,
                cor_secundaria: document.getElementById('input-cor-secundaria')?.value,
                cor_fundo: document.getElementById('input-cor-fundo')?.value,
                cor_superficie: document.getElementById('input-cor-superficie')?.value,
                cor_texto: document.getElementById('input-cor-texto')?.value,
                cor_texto_secundario: document.getElementById('input-cor-texto-secundario')?.value,
                fonte_principal: document.getElementById('select-fonte-principal')?.value,
                fonte_titulos: document.getElementById('select-fonte-titulos')?.value,
                radius_padrao: document.getElementById('select-radius-padrao')?.value,
                sombra_padrao: document.getElementById('select-sombra-padrao')?.value,
            };

            try {
                if (window.BioSiteAutosave) {
                    window.BioSiteAutosave.definirStatus('salvando');
                }

                const url = `/painel/sites/${siteUuid}/editor/design/salvar/`;
                const resp = await window.BioSiteApi.post(url, payload);

                if (resp && resp.ok) {
                    if (resp.tokens) {
                        aplicarTokensNoCanvas(resp.tokens);
                    }
                    if (window.BioSiteAutosave) {
                        window.BioSiteAutosave.definirStatus('salvo');
                    }
                } else {
                    if (window.BioSiteAutosave) {
                        window.BioSiteAutosave.definirStatus('erro');
                    }
                }
            } catch (err) {
                console.error('Erro ao salvar design global:', err);
                if (window.BioSiteAutosave) {
                    window.BioSiteAutosave.definirStatus('erro');
                }
            }
        }, 500);
    }

    function sincronizarInputsCor(idPicker, idHex, propVar) {
        const picker = document.getElementById(idPicker);
        const hex = document.getElementById(idHex);
        if (!picker || !hex) return;

        picker.addEventListener('input', (e) => {
            const val = e.target.value;
            hex.value = val.toUpperCase();
            const root = document.querySelector('.biosite-canvas-root');
            if (root) root.style.setProperty(propVar, val);
            atualizarBadgeContraste();
            dispararSalvar();
        });

        hex.addEventListener('input', (e) => {
            let val = e.target.value.trim();
            if (!val.startsWith('#')) val = '#' + val;
            if (/^#[0-9A-Fa-f]{6}$/.test(val)) {
                picker.value = val;
                const root = document.querySelector('.biosite-canvas-root');
                if (root) root.style.setProperty(propVar, val);
                atualizarBadgeContraste();
                dispararSalvar();
            }
        });
    }

    function aplicarPreset(preset) {
        if (!preset) return;

        const campos = [
            ['input-cor-primaria', 'hex-cor-primaria', preset.cor_primaria, '--cor-primaria'],
            ['input-cor-secundaria', 'hex-cor-secundaria', preset.cor_secundaria, '--cor-secundaria'],
            ['input-cor-fundo', 'hex-cor-fundo', preset.cor_fundo, '--cor-fundo'],
            ['input-cor-superficie', 'hex-cor-superficie', preset.cor_superficie, '--cor-superficie'],
            ['input-cor-texto', 'hex-cor-texto', preset.cor_texto, '--cor-texto'],
            ['input-cor-texto-secundario', 'hex-cor-texto-secundario', preset.cor_texto_secundario, '--cor-texto-secundario'],
        ];

        campos.forEach(([idPicker, idHex, valor, cssVar]) => {
            const p = document.getElementById(idPicker);
            const h = document.getElementById(idHex);
            if (p && valor) p.value = valor;
            if (h && valor) h.value = valor.toUpperCase();
            const root = document.querySelector('.biosite-canvas-root');
            if (root && valor) root.style.setProperty(cssVar, valor);
        });

        if (preset.fonte_principal) {
            const fp = document.getElementById('select-fonte-principal');
            if (fp) fp.value = preset.fonte_principal;
            const root = document.querySelector('.biosite-canvas-root');
            if (root) root.style.setProperty('--fonte-principal', preset.fonte_principal);
        }

        if (preset.fonte_titulos) {
            const ft = document.getElementById('select-fonte-titulos');
            if (ft) ft.value = preset.fonte_titulos;
            const root = document.querySelector('.biosite-canvas-root');
            if (root) root.style.setProperty('--fonte-titulos', preset.fonte_titulos);
        }

        if (preset.radius_padrao) {
            const r = document.getElementById('select-radius-padrao');
            if (r) r.value = preset.radius_padrao;
            const root = document.querySelector('.biosite-canvas-root');
            if (root) root.style.setProperty('--radius-padrao', preset.radius_padrao);
        }

        if (preset.sombra_padrao) {
            const s = document.getElementById('select-sombra-padrao');
            if (s) s.value = preset.sombra_padrao;
        }

        atualizarBadgeContraste();
        dispararSalvar();
    }

    function init(uuid) {
        siteUuid = uuid;

        sincronizarInputsCor('input-cor-primaria', 'hex-cor-primaria', '--cor-primaria');
        sincronizarInputsCor('input-cor-secundaria', 'hex-cor-secundaria', '--cor-secundaria');
        sincronizarInputsCor('input-cor-fundo', 'hex-cor-fundo', '--cor-fundo');
        sincronizarInputsCor('input-cor-superficie', 'hex-cor-superficie', '--cor-superficie');
        sincronizarInputsCor('input-cor-texto', 'hex-cor-texto', '--cor-texto');
        sincronizarInputsCor('input-cor-texto-secundario', 'hex-cor-texto-secundario', '--cor-texto-secundario');

        const fp = document.getElementById('select-fonte-principal');
        if (fp) {
            fp.addEventListener('change', (e) => {
                const root = document.querySelector('.biosite-canvas-root');
                if (root) root.style.setProperty('--fonte-principal', e.target.value);
                dispararSalvar();
            });
        }

        const ft = document.getElementById('select-fonte-titulos');
        if (ft) {
            ft.addEventListener('change', (e) => {
                const root = document.querySelector('.biosite-canvas-root');
                if (root) root.style.setProperty('--fonte-titulos', e.target.value);
                dispararSalvar();
            });
        }

        const r = document.getElementById('select-radius-padrao');
        if (r) {
            r.addEventListener('change', (e) => {
                const root = document.querySelector('.biosite-canvas-root');
                if (root) root.style.setProperty('--radius-padrao', e.target.value);
                dispararSalvar();
            });
        }

        const s = document.getElementById('select-sombra-padrao');
        if (s) {
            s.addEventListener('change', () => {
                dispararSalvar();
            });
        }

        // Configuração dos cartões de presets visuais
        const cards = document.querySelectorAll('.design-preset-card');
        cards.forEach(card => {
            card.addEventListener('click', () => {
                cards.forEach(c => c.classList.remove('active'));
                card.classList.add('active');

                try {
                    const presetJson = card.getAttribute('data-preset');
                    if (presetJson) {
                        const preset = JSON.parse(presetJson);
                        aplicarPreset(preset);
                    }
                } catch (e) {
                    console.error('Erro ao ler preset:', e);
                }
            });
        });

        atualizarBadgeContraste();
    }

    return {
        init: init,
        aplicarTokensNoCanvas: aplicarTokensNoCanvas,
        aplicarPreset: aplicarPreset,
    };
})();
