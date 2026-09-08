/**
 * BioSite NFC — Utilitários e Interações do Painel Administrativo.
 * JavaScript puro (Vanilla JS), moderno, modular e acessível.
 */

(function () {
    "use strict";

    // --------------------------------------------------------------------------
    // 1. UTILITÁRIOS: CSRF & COOKIES
    // --------------------------------------------------------------------------
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== "") {
            const cookies = document.cookie.split(";");
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + "=")) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    function getCsrfToken() {
        const input = document.querySelector("[name=csrfmiddlewaretoken]");
        if (input && input.value) return input.value;
        return getCookie("csrftoken") || "";
    }

    // --------------------------------------------------------------------------
    // 2. SISTEMA DE TOASTS FLUTUANTES (FEEDBACK NÃO INTRUSIVO)
    // --------------------------------------------------------------------------
    window.showToast = function (message, type = "info") {
        let container = document.getElementById("toast-container");
        if (!container) {
            container = document.createElement("div");
            container.id = "toast-container";
            container.className = "toast-container";
            container.setAttribute("aria-live", "polite");
            container.setAttribute("aria-atomic", "true");
            document.body.appendChild(container);
        }

        const toast = document.createElement("div");
        toast.className = `toast toast-${type}`;

        let iconHtml = "ℹ";
        if (type === "success") iconHtml = "✓";
        else if (type === "error") iconHtml = "✕";
        else if (type === "warning") iconHtml = "⚠";

        toast.innerHTML = `
            <span class="toast-icon">${iconHtml}</span>
            <span class="toast-message">${message}</span>
        `;

        container.appendChild(toast);

        // Fade out e remoção automática
        setTimeout(() => {
            toast.classList.add("fade-out");
            setTimeout(() => {
                toast.remove();
            }, 300);
        }, 3500);
    };

    // --------------------------------------------------------------------------
    // 3. INICIALIZAÇÃO PRINCIPAL DO DOM
    // --------------------------------------------------------------------------
    document.addEventListener("DOMContentLoaded", () => {
        // 3.1. ALTERNADOR DE TEMA DARK / LIGHT
        const modeSwitch = document.querySelector(".mode-switch");
        if (modeSwitch) {
            // Sincronizar estado inicial com localStorage
            const savedTheme = localStorage.getItem("biosite_painel_theme");
            if (savedTheme === "light") {
                document.documentElement.classList.add("light");
                modeSwitch.classList.add("active");
            } else {
                document.documentElement.classList.remove("light");
                modeSwitch.classList.remove("active");
            }

            modeSwitch.addEventListener("click", () => {
                const isLight = document.documentElement.classList.toggle("light");
                modeSwitch.classList.toggle("active", isLight);
                try {
                    localStorage.setItem("biosite_painel_theme", isLight ? "light" : "dark");
                } catch (e) {
                    console.warn("Não foi possível persistir tema no localStorage:", e);
                }
            });
        }

        // 3.2. ALTERNADOR DE VISUALIZAÇÃO: TABELA (LIST) VS GRADE (GRID)
        const btnViewList = document.querySelector(".js-view-list");
        const btnViewGrid = document.querySelector(".js-view-grid");
        const sitesAreaWrapper = document.getElementById("sitesAreaWrapper");

        if (sitesAreaWrapper && btnViewList && btnViewGrid) {
            // Restaurar preferência do usuário
            const savedView = localStorage.getItem("biosite_view_mode") || "tableView";
            if (savedView === "gridView") {
                sitesAreaWrapper.classList.remove("tableView");
                sitesAreaWrapper.classList.add("gridView");
                btnViewGrid.classList.add("active");
                btnViewList.classList.remove("active");
            } else {
                sitesAreaWrapper.classList.remove("gridView");
                sitesAreaWrapper.classList.add("tableView");
                btnViewList.classList.add("active");
                btnViewGrid.classList.remove("active");
            }

            btnViewList.addEventListener("click", () => {
                sitesAreaWrapper.classList.remove("gridView");
                sitesAreaWrapper.classList.add("tableView");
                btnViewList.classList.add("active");
                btnViewGrid.classList.remove("active");
                try {
                    localStorage.setItem("biosite_view_mode", "tableView");
                } catch (e) {}
            });

            btnViewGrid.addEventListener("click", () => {
                sitesAreaWrapper.classList.remove("tableView");
                sitesAreaWrapper.classList.add("gridView");
                btnViewGrid.classList.add("active");
                btnViewList.classList.remove("active");
                try {
                    localStorage.setItem("biosite_view_mode", "gridView");
                } catch (e) {}
            });
        }

        // 3.3. MENU FLUTUANTE DE FILTROS
        const filterToggleBtn = document.querySelector(".jsFilter");
        const filterMenu = document.querySelector(".filter-menu");

        if (filterToggleBtn && filterMenu) {
            filterToggleBtn.addEventListener("click", (e) => {
                e.stopPropagation();
                filterMenu.classList.toggle("active");
            });

            // Fechar ao clicar fora
            document.addEventListener("click", (e) => {
                if (!filterMenu.contains(e.target) && !filterToggleBtn.contains(e.target)) {
                    filterMenu.classList.remove("active");
                }
            });

            // Fechar ao pressionar ESC
            document.addEventListener("keydown", (e) => {
                if (e.key === "Escape" && filterMenu.classList.contains("active")) {
                    filterMenu.classList.remove("active");
                }
            });
        }

        // 3.4. MENU LATERAL EM DISPOSITIVOS MÓVEIS (DRAWER & BACKDROP)
        const mobileMenuToggle = document.querySelector(".js-mobile-menu-toggle");
        const sidebarCloseBtn = document.querySelector(".js-sidebar-close");
        const sidebar = document.getElementById("appSidebar");
        const backdrop = document.querySelector(".js-sidebar-backdrop");

        function openSidebar() {
            if (sidebar) sidebar.classList.add("open");
            if (backdrop) backdrop.classList.add("active");
            document.body.style.overflow = "hidden";
        }

        function closeSidebar() {
            if (sidebar) sidebar.classList.remove("open");
            if (backdrop) backdrop.classList.remove("active");
            document.body.style.overflow = "";
        }

        if (mobileMenuToggle) {
            mobileMenuToggle.addEventListener("click", (e) => {
                e.stopPropagation();
                openSidebar();
            });
        }

        if (sidebarCloseBtn) {
            sidebarCloseBtn.addEventListener("click", (e) => {
                e.stopPropagation();
                closeSidebar();
            });
        }

        if (backdrop) {
            backdrop.addEventListener("click", () => {
                closeSidebar();
            });
        }

        // 3.5. MENUS SECUNDÁRIOS DE AÇÕES (⋮)
        document.addEventListener("click", (e) => {
            const btnMore = e.target.closest(".js-action-dropdown-btn");

            // Se clicou em um botão de menu ⋮
            if (btnMore) {
                e.stopPropagation();
                const currentWrapper = btnMore.closest(".action-more-wrapper");
                const currentMenu = currentWrapper?.querySelector(".action-dropdown-menu");

                // Fecha outros menus abertos
                document.querySelectorAll(".action-dropdown-menu.active").forEach((menu) => {
                    if (menu !== currentMenu) {
                        menu.classList.remove("active");
                    }
                });

                if (currentMenu) {
                    currentMenu.classList.toggle("active");
                }
                return;
            }

            // Se clicou dentro de um dropdown menu (sem ser link de fechamento)
            if (e.target.closest(".action-dropdown-menu")) {
                return;
            }

            // Se clicou fora, fecha todos os menus ⋮
            document.querySelectorAll(".action-dropdown-menu.active").forEach((menu) => {
                menu.classList.remove("active");
            });
        });

        // 3.6. SWITCH OPERACIONAL ONLINE / OFFLINE (PUBLICAÇÃO / DESPUBLICAÇÃO ASSÍNCRONA)
        document.addEventListener("click", async (e) => {
            const switchBtn = e.target.closest(".switch-status");
            if (!switchBtn) return;

            e.preventDefault();
            e.stopPropagation();

            if (switchBtn.disabled) return;

            const uuid = switchBtn.getAttribute("data-uuid");
            const currentStatus = switchBtn.getAttribute("data-status"); // 'online' ou 'offline'
            const urlDespublicar = switchBtn.getAttribute("data-url-despublicar");
            const urlPublicar = switchBtn.getAttribute("data-url-publicar");
            const csrfToken = getCsrfToken();

            if (!uuid || (!urlDespublicar && !urlPublicar)) return;

            const isCurrentlyOnline = currentStatus === "online";
            const targetUrl = isCurrentlyOnline ? urlDespublicar : urlPublicar;
            const targetAction = isCurrentlyOnline ? "despublicar" : "publicar";

            // Desativa todos os switches deste UUID durante a requisição
            const relatedSwitches = document.querySelectorAll(`.switch-status[data-uuid="${uuid}"]`);
            relatedSwitches.forEach((btn) => {
                btn.disabled = true;
            });

            try {
                const requestOptions = {
                    method: "POST",
                    headers: {
                        "X-CSRFToken": csrfToken,
                        "X-Requested-With": "XMLHttpRequest",
                        "Content-Type": "application/json",
                    },
                };

                if (targetAction === "publicar") {
                    requestOptions.body = JSON.stringify({ forcar: true });
                }

                const response = await fetch(targetUrl, requestOptions);
                const data = await response.json();

                if (response.ok && data.ok) {
                    const isNowOnline = data.esta_publicado !== undefined ? data.esta_publicado : !isCurrentlyOnline;

                    // 1. Atualizar todos os switches para esse UUID (tabela e grid)
                    relatedSwitches.forEach((btn) => {
                        if (isNowOnline) {
                            btn.classList.add("active");
                            btn.setAttribute("data-status", "online");
                            btn.closest(".switch-wrapper")?.setAttribute("title", "Clique para retirar do ar imediatamente");
                        } else {
                            btn.classList.remove("active");
                            btn.setAttribute("data-status", "offline");
                            btn.closest(".switch-wrapper")?.setAttribute("title", "Clique para colocar o site no ar imediatamente");
                        }
                    });

                    // 2. Atualizar badges de status para esse UUID
                    const badgeContainers = document.querySelectorAll(`.status-badge-container[data-site-uuid="${uuid}"]`);
                    badgeContainers.forEach((container) => {
                        if (isNowOnline) {
                            container.innerHTML = `
                                <span class="status status-active" title="Publicado e ativo para o público">
                                    <span class="status-dot"></span> No ar
                                </span>
                            `;
                        } else {
                            container.innerHTML = `
                                <span class="status status-disabled" title="Site fora do ar (despublicado)">
                                    <span class="status-dot"></span> Fora do ar
                                </span>
                            `;
                        }
                    });

                    // 3. Atualizar botões de "Abrir"
                    const openButtons = document.querySelectorAll(`[data-site-uuid="${uuid}"] .btn-action-open`);
                    openButtons.forEach((btnOpen) => {
                        if (isNowOnline) {
                            btnOpen.classList.remove("disabled");
                            btnOpen.removeAttribute("aria-disabled");
                            btnOpen.setAttribute("title", "Abrir site publicado em nova aba");
                            if (data.url_publica) {
                                btnOpen.setAttribute("href", data.url_publica);
                            }
                        } else {
                            btnOpen.classList.add("disabled");
                            btnOpen.setAttribute("aria-disabled", "true");
                            btnOpen.setAttribute("title", "Site fora do ar (indisponível para o público)");
                        }
                    });

                    // 4. Toast de confirmação
                    const defaultMsg = isNowOnline ? "Site publicado com sucesso!" : "Site retirado do ar com sucesso.";
                    window.showToast(data.mensagem || defaultMsg, isNowOnline ? "success" : "info");

                } else {
                    const errorMsg = data.erro || data.mensagem || "Ocorreu um erro ao processar a solicitação.";
                    window.showToast(errorMsg, "error");
                }
            } catch (err) {
                console.error("Erro na requisição de publicação:", err);
                window.showToast("Falha na comunicação com o servidor. Tente novamente.", "error");
            } finally {
                relatedSwitches.forEach((btn) => {
                    btn.disabled = false;
                });
            }
        });

        // 3.7. ALTERNADOR DE VISIBILIDADE DE SENHA (UTILITÁRIO EXISTENTE)
        const toggleButtons = document.querySelectorAll(".btn-toggle-password");
        toggleButtons.forEach((button) => {
            button.addEventListener("click", (e) => {
                e.preventDefault();
                const targetId = button.getAttribute("data-target");
                const input = targetId ? document.getElementById(targetId) : button.closest(".input-password-wrapper")?.querySelector("input");

                if (!input) return;

                const isPassword = input.getAttribute("type") === "password";
                input.setAttribute("type", isPassword ? "text" : "password");
                button.textContent = isPassword ? "Ocultar" : "Mostrar";
                button.setAttribute("aria-pressed", isPassword ? "true" : "false");
                button.setAttribute("aria-label", isPassword ? "Ocultar senha" : "Exibir senha");
            });
        });
    });
})();
