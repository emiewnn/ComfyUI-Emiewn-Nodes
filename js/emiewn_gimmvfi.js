import { app } from "../../scripts/app.js";

const gimmStyle = document.createElement('style');
gimmStyle.textContent = `
    .emiewn-gimm-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 4px 10px;
        background: linear-gradient(135deg, #1e2a1e 0%, #1c1c1c 100%);
        border: 1px solid #2d4a2d;
        border-radius: 6px;
        font-family: 'Segoe UI', sans-serif;
        font-size: 11px;
        color: #cfcfcf;
        transition: all 0.3s ease;
        cursor: default;
    }
    .emiewn-gimm-badge:hover {
        border-color: #6ee66e;
        box-shadow: 0 0 8px rgba(110, 230, 110, 0.2);
        transform: translateY(-1px);
    }
    .emiewn-gimm-icon {
        font-size: 13px;
        animation: emiewn-spin-gimm 3s linear infinite;
    }
    .emiewn-gimm-text {
        font-weight: 500;
        color: #8cd68c;
        letter-spacing: 0.3px;
    }

    .emiewn-interp-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 4px 10px;
        background: linear-gradient(135deg, #2d2346 0%, #1c1c1c 100%);
        border: 1px solid #3a2d5c;
        border-radius: 6px;
        font-family: 'Segoe UI', sans-serif;
        font-size: 11px;
        color: #cfcfcf;
        transition: all 0.3s ease;
        cursor: default;
    }
    .emiewn-interp-badge:hover {
        border-color: #8c7ae6;
        box-shadow: 0 0 8px rgba(140, 122, 230, 0.25);
        transform: translateY(-1px);
    }
    .emiewn-interp-icon {
        font-size: 13px;
        animation: emiewn-bounce-interp 1.5s ease-in-out infinite;
    }
    .emiewn-interp-text {
        font-weight: 500;
        color: #a89cd6;
        letter-spacing: 0.3px;
    }

    @keyframes emiewn-spin-gimm {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
    @keyframes emiewn-bounce-interp {
        0%, 100% { transform: translateY(0); }
        50% { transform: translateY(-2px); }
    }
`;
document.head.appendChild(gimmStyle);

app.registerExtension({
    name: "Emiewn.GIMMVFI",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {

        if (nodeData.name === "EmiewnLoadGIMMVFI") {
            const onNodeCreated = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function () {
                const r = onNodeCreated ? onNodeCreated.apply(this, arguments) : undefined;
                const node = this;

                const div = document.createElement("div");
                div.style.cssText = "display:flex; justify-content:center; padding:6px 0;";

                const badge = document.createElement("div");
                badge.className = "emiewn-gimm-badge";
                badge.innerHTML = `
                    <span class="emiewn-gimm-icon">⚙️</span>
                    <span class="emiewn-gimm-text">GIMM-VFI Engine</span>
                `;
                div.appendChild(badge);

                node.addDOMWidget("gimm_badge", "custom", div, {
                    serialize: false,
                    hideOnZoom: true
                });

                node.setSize([240, 140]);

                return r;
            };
        }

        if (nodeData.name === "EmiewnGIMMVFIInterpolate") {
            const onNodeCreated = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function () {
                const r = onNodeCreated ? onNodeCreated.apply(this, arguments) : undefined;
                const node = this;

                const div = document.createElement("div");
                div.style.cssText = "display:flex; justify-content:center; padding:6px 0;";

                const badge = document.createElement("div");
                badge.className = "emiewn-interp-badge";
                badge.innerHTML = `
                    <span class="emiewn-interp-icon">🎞️</span>
                    <span class="emiewn-interp-text">Frame Interpolator</span>
                `;
                div.appendChild(badge);

                node.addDOMWidget("interp_badge", "custom", div, {
                    serialize: false,
                    hideOnZoom: true
                });

                node.setSize([260, 210]);

                return r;
            };
        }
    }
});
