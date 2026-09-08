/**
 * BioSite Analytics — First-Party & Privacy-Friendly (Prompt 11)
 *
 * Características:
 * 1. Zero cookies, zero identificação pessoal, zero trackers de terceiros.
 * 2. Fail-open absoluto: falhas de rede nunca atrasam ou impedem a navegação do visitante.
 * 3. Assíncrono e não-bloqueante: usa navigator.sendBeacon ou fetch com keepalive.
 * 4. Delegação de eventos única para alta performance mobile.
 */
(function () {
    "use strict";

    var cfg = window.__BIO_ANALYTICS__;
    if (!cfg || !cfg.endpoint) return;

    var endpoint = cfg.endpoint;

    function enviarBeacon(payload) {
        try {
            var corpo = JSON.stringify(payload);
            if (navigator.sendBeacon) {
                navigator.sendBeacon(endpoint, corpo);
            } else if (window.fetch) {
                fetch(endpoint, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: corpo,
                    keepalive: true,
                    credentials: "omit",
                    mode: "same-origin"
                }).catch(function () {});
            }
        } catch (e) {
            // Fail-open: Nunca interfere na experiência do usuário
        }
    }

    // 1. Dispara Page View após renderização do DOM
    if (cfg.pageviewToken) {
        if (document.readyState === "loading") {
            document.addEventListener("DOMContentLoaded", function () {
                enviarBeacon({ token: cfg.pageviewToken });
            });
        } else {
            enviarBeacon({ token: cfg.pageviewToken });
        }
    }

    // 2. Delegação de eventos para cliques em componentes rastreáveis
    document.addEventListener(
        "click",
        function (event) {
            try {
                var alvo = event.target;
                if (!alvo) return;
                var trackable = alvo.closest("[data-event-token]");
                if (!trackable) return;

                var token = trackable.getAttribute("data-event-token");
                if (token) {
                    enviarBeacon({ token: token });
                }
            } catch (e) {
                // Fail-open: Ação original (ex: WhatsApp, tel, URL) segue desimpedida
            }
        },
        true
    );
})();
