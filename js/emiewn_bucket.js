import { app } from "../../scripts/app.js";

const bucketStyle = document.createElement('style');
bucketStyle.textContent = `
    .emiewn-bucket-badge {
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
    .emiewn-bucket-badge:hover {
        border-color: #8c7ae6;
        box-shadow: 0 0 8px rgba(140, 122, 230, 0.25);
        transform: translateY(-1px);
    }
    .emiewn-bucket-icon {
        font-size: 13px;
        animation: emiewn-pulse-bucket 2s ease-in-out infinite;
    }
    .emiewn-bucket-text {
        font-weight: 500;
        color: #a89cd6;
        letter-spacing: 0.3px;
    }
    @keyframes emiewn-pulse-bucket {
        0%, 100% { opacity: 0.7; transform: scale(1); }
        50% { opacity: 1; transform: scale(1.1); }
    }
`;
document.head.appendChild(bucketStyle);

app.registerExtension({
    name: "Emiewn.NearestI2VRes",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === "EmiewnNearestI2VRes") {

            const onNodeCreated = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function () {
                const r = onNodeCreated ? onNodeCreated.apply(this, arguments) : undefined;
                const node = this;

                const div = document.createElement("div");
                div.style.cssText = "display:flex; justify-content:center; padding:6px 0;";

                const badge = document.createElement("div");
                badge.className = "emiewn-bucket-badge";
                badge.innerHTML = `
                    <span class="emiewn-bucket-icon">📐</span>
                    <span class="emiewn-bucket-text">I2V Bucket Resolver</span>
                `;
                div.appendChild(badge);

                node.addDOMWidget("bucket_badge", "custom", div, {
                    serialize: false,
                    hideOnZoom: true
                });

                node.setSize([220, 120]);

                return r;
            };
        }
    }
});
