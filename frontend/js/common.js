(function (window) {
    function getApiBase() {
        var configured = (localStorage.getItem("api_base") || "").trim();
        if (configured) return configured;
        var host = window.location.hostname;
        if (host === "localhost" || host === "127.0.0.1") return "http://127.0.0.1:5000";
        return "";
    }

    function getToken() {
        return localStorage.getItem("auth_token") || localStorage.getItem("token") || "";
    }

    function qs(selector, root) {
        return (root || document).querySelector(selector);
    }

    function qsa(selector, root) {
        return Array.from((root || document).querySelectorAll(selector));
    }

    function formatDate(value) {
        if (!value) return "-";
        var d = new Date(String(value).replace(" ", "T"));
        if (Number.isNaN(d.getTime())) return String(value);
        return d.toLocaleString("zh-CN", { hour12: false });
    }

    function escapeHtml(value) {
        return String(value || "")
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/\"/g, "&quot;")
            .replace(/'/g, "&#39;");
    }

    window.CP = {
        getApiBase: getApiBase,
        getToken: getToken,
        qs: qs,
        qsa: qsa,
        formatDate: formatDate,
        escapeHtml: escapeHtml,
    };
})(window);
