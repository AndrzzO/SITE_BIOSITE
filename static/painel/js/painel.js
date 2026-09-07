/**
 * Utilitários interativos para o Painel Administrativo BioSite NFC.
 * Livre de bibliotecas externas pesadas e totalmente acessível.
 */

document.addEventListener("DOMContentLoaded", () => {
    // Alternador de visibilidade de senha (acessível)
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
