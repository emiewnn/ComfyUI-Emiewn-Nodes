import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

const cropStyle = document.createElement('style');
cropStyle.textContent = `
    .emiewn-backdrop {
        position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
        background: rgba(0, 0, 0, 0.7); z-index: 20000;
        display: flex; align-items: center; justify-content: center;
        opacity: 0; transition: opacity 0.2s ease; backdrop-filter: blur(5px);
    }
    .emiewn-backdrop.visible { opacity: 1; }
    .emiewn-window {
        width: 85%; max-width: 1000px; background: #18181b; border: 1px solid #3f3f46;
        border-radius: 12px; box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
        display: flex; flex-direction: column; padding: 24px; box-sizing: border-box; font-family: sans-serif;
    }
    .emiewn-header {
        display: flex; justify-content: space-between; align-items: center;
        margin-bottom: 20px; border-bottom: 1px solid #27272a; padding-bottom: 12px;
    }
    .emiewn-title { font-size: 20px; font-weight: 600; color: #fafafa; }
    .emiewn-viewport {
        position: relative; background: #09090b; border-radius: 8px; overflow: hidden;
        margin: 0 auto; max-height: 60vh; display: flex; justify-content: center; align-items: center;
    }
    .emiewn-image { max-width: 100%; max-height: 60vh; display: block; user-select: none; }
    .emiewn-box { position: absolute; border: 1.5px solid #fff; box-shadow: 0 0 0 9999px rgba(0, 0, 0, 0.6); cursor: move; }
    .emiewn-handle { width: 12px; height: 12px; background: #8b5cf6; border: 2px solid #fff; position: absolute; border-radius: 50%; z-index: 10; }
    .h-nw { top: -7px; left: -7px; cursor: nw-resize; } .h-ne { top: -7px; right: -7px; cursor: ne-resize; }
    .h-sw { bottom: -7px; left: -7px; cursor: sw-resize; } .h-se { bottom: -7px; right: -7px; cursor: se-resize; }
    .h-n { top: -7px; left: 50%; margin-left: -6px; cursor: n-resize; } .h-s { bottom: -7px; left: 50%; margin-left: -6px; cursor: s-resize; }
    .h-w { left: -7px; top: 50%; margin-top: -6px; cursor: w-resize; } .h-e { right: -7px; top: 50%; margin-top: -6px; cursor: e-resize; }
    .emiewn-footer { margin-top: 24px; display: flex; justify-content: flex-end; gap: 12px; }
    .emiewn-btn { padding: 10px 20px; border-radius: 8px; font-size: 14px; font-weight: 500; cursor: pointer; border: none; transition: 0.2s; }
    .emiewn-btn-primary { background: #8b5cf6; color: white; } .emiewn-btn-primary:hover { background: #a78bfa; }
    .emiewn-btn-sec { background: #27272a; color: #d4d4d8; } .emiewn-btn-sec:hover { background: #3f3f46; }
`;
document.head.appendChild(cropStyle);

app.registerExtension({
    name: "Emiewn.ImgCrop",
    async setup() {
        api.addEventListener("emiewn.crop_request", (e) => {
            createCropWindow(e.detail.node_id, e.detail.image_url);
        });

        const bodyObserver = new MutationObserver((mutations) => {
            for (const mutation of mutations) {
                for (const node of mutation.addedNodes) {
                    if (node.classList && (node.classList.contains('comfy-modal') || node.querySelector('.comfy-modal-content'))) {
                        if (node.innerText.includes("Emiewn")) {
                            node.style.display = "none";
                            setTimeout(() => node.remove(), 1); 
                        }
                    }
                }
            }
        });
        bodyObserver.observe(document.body, { childList: true, subtree: true });
    },

    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name === "EmiewnImgCrop") {
            const onNodeCreated = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function () {
                const r = onNodeCreated ? onNodeCreated.apply(this, arguments) : undefined;
                let w = this.widgets?.find(w => w.name === "crop_data");
                if (!w) w = this.addWidget("text", "crop_data", "", null, { serialize: true });
                w.type = "hidden";
                return r;
            };
        }
    }
});

function createCropWindow(nodeId, imageUrl) {
    if (document.querySelector('.emiewn-backdrop')) return;
    const backdrop = document.createElement('div');
    backdrop.className = 'emiewn-backdrop';
    backdrop.innerHTML = `
        <div class="emiewn-window">
            <div class="emiewn-header"><div class="emiewn-title">Quick Crop</div></div>
            <div class="emiewn-viewport" id="vp">
                <img src="${imageUrl}" class="emiewn-image" id="img">
                <div class="emiewn-box" id="box" style="display:none">
                    <div class="emiewn-handle h-nw" data-dir="nw"></div><div class="emiewn-handle h-n" data-dir="n"></div><div class="emiewn-handle h-ne" data-dir="ne"></div>
                    <div class="emiewn-handle h-e" data-dir="e"></div><div class="emiewn-handle h-se" data-dir="se"></div><div class="emiewn-handle h-s" data-dir="s"></div>
                    <div class="emiewn-handle h-sw" data-dir="sw"></div><div class="emiewn-handle h-w" data-dir="w"></div>
                </div>
            </div>
            <div class="emiewn-footer">
                <button class="emiewn-btn emiewn-btn-sec" id="btnFull">Skip</button>
                <button class="emiewn-btn emiewn-btn-primary" id="btnCrop">Apply</button>
            </div>
        </div>`;
    document.body.appendChild(backdrop);
    requestAnimationFrame(() => backdrop.classList.add('visible'));

    const img = backdrop.querySelector('#img'), box = backdrop.querySelector('#box'), vp = backdrop.querySelector('#vp');
    let rect = { x: 0, y: 0, w: 0, h: 0 }, imgW = 0, imgH = 0;

    const init = () => {
        imgW = img.offsetWidth; imgH = img.offsetHeight;
        rect = { x: imgW * 0.1, y: imgH * 0.1, w: imgW * 0.8, h: imgH * 0.8 };
        updateBox(); box.style.display = 'block';
    };
    if (img.complete) init(); else img.onload = init;
    const updateBox = () => {
        box.style.left = rect.x + 'px'; box.style.top = rect.y + 'px';
        box.style.width = rect.w + 'px'; box.style.height = rect.h + 'px';
    };

    let action = null, startX = 0, startY = 0, startRect = {};
    const onDown = (e) => {
        const t = e.target;
        if (t.classList.contains('emiewn-handle')) action = t.dataset.dir;
        else if (t.classList.contains('emiewn-box')) action = 'move';
        else return;
        startX = e.clientX; startY = e.clientY; startRect = { ...rect };
        e.preventDefault();
        window.addEventListener('mousemove', onMove);
        window.addEventListener('mouseup', onUp);
    };
    const onMove = (e) => {
        if (!action) return;
        const dx = e.clientX - startX, dy = e.clientY - startY;
        let nx = startRect.x, ny = startRect.y, nw = startRect.w, nh = startRect.h;
        if (action === 'move') { nx += dx; ny += dy; }
        else {
            if (action.includes('e')) nw = startRect.w + dx; if (action.includes('s')) nh = startRect.h + dy;
            if (action.includes('w')) { nx = startRect.x + dx; nw = startRect.w - dx; }
            if (action.includes('n')) { ny = startRect.y + dy; nh = startRect.h - dy; }
        }
        nw = Math.max(20, nw); nh = Math.max(20, nh);
        nx = Math.max(0, Math.min(nx, imgW - nw)); ny = Math.max(0, Math.min(ny, imgH - nh));
        if (nx + nw > imgW) nw = imgW - nx; if (ny + nh > imgH) nh = imgH - ny;
        rect = { x: nx, y: ny, w: nw, h: nh };
        updateBox();
    };
    const onUp = () => { action = null; window.removeEventListener('mousemove', onMove); window.removeEventListener('mouseup', onUp); };
    vp.addEventListener('mousedown', onDown);

    const submit = (bypass) => {
        const node = app.graph.getNodeById(nodeId);
        const cropWidget = node.widgets.find(w => w.name === "crop_data");
        const bypassWidget = node.widgets.find(w => w.name === "bypass_node");
        
        if (bypass) {
            bypassWidget.value = true;
        } else {
            const scale = img.naturalWidth / imgW;
            cropWidget.value = [Math.round(rect.x * scale), Math.round(rect.y * scale), Math.round(rect.w * scale), Math.round(rect.h * scale)].join(",");
        }
        
        backdrop.remove();
        app.queuePrompt(0);
        setTimeout(() => {
            cropWidget.value = "";
            bypassWidget.value = false;
        }, 500);
    };

    backdrop.querySelector('#btnCrop').onclick = () => submit(false);
    backdrop.querySelector('#btnFull').onclick = () => submit(true);
}