(function () {
    // Basic loader script
    const currentScript = document.currentScript;
    const clientId = currentScript.getAttribute('data-client-id');
    const apiBase = currentScript.getAttribute('data-api-base') || 'http://localhost:8000';

    if (!clientId) {
        console.error('PolicyWidget: data-client-id is required');
        return;
    }

    async function loadWidget() {
        try {
            const response = await fetch(`${apiBase}/api/widget/content/${clientId}`);
            if (!response.ok) throw new Error('Failed to load policy');

            const data = await response.json();

            // 1. Inject JSON-LD for SEO
            const script = document.createElement('script');
            script.type = 'application/ld+json';
            script.text = JSON.stringify(data.json_ld);
            document.head.appendChild(script);

            // 2. Render Policy in Shadow DOM
            const container = document.createElement('div');
            container.id = `policy-widget-${clientId}`;
            currentScript.parentNode.insertBefore(container, currentScript);

            const shadow = container.attachShadow({ mode: 'open' });

            // Add some base styles
            const style = document.createElement('style');
            style.textContent = `
                :host { display: block; font-family: sans-serif; }
                .policy-content { padding: 20px; border: 1px solid #ddd; border-radius: 8px; }
            `;
            shadow.appendChild(style);

            const contentDiv = document.createElement('div');
            contentDiv.className = 'policy-content';
            contentDiv.innerHTML = data.html_content;
            shadow.appendChild(contentDiv);

        } catch (e) {
            console.error('PolicyWidget Error:', e);
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', loadWidget);
    } else {
        loadWidget();
    }
})();
