import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

const style = document.createElement('style');
style.textContent = `
    .emiewn-paste-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center; 
        width: 100%;
        height: 100%;
        background: #1c1c1c;
        border-radius: 4px;
        border: 1px solid #333;
        color: #cfcfcf;
        font-family: 'Segoe UI', sans-serif;
        text-align: center;
        box-sizing: border-box;
        overflow: hidden;
        position: relative;
        cursor: pointer;
        outline: none;
    }
    
    .emiewn-paste-container:focus, .emiewn-paste-container.focused {
        border-color: #8c7ae6;
        box-shadow: 0 0 0 2px rgba(140, 122, 230, 0.3);
    }

    .emiewn-paste-content {
        padding: 20px;
        pointer-events: none;
        z-index: 10;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        height: 100%;
    }

    .emiewn-icon {
        font-size: 28px;
        margin-bottom: 8px;
        color: #8c7ae6;
    }

    .emiewn-text {
        font-size: 12px;
        font-weight: 500;
        color: #a0a0a0;
    }

    .emiewn-preview {
        width: 100%;
        flex: 1;
        object-fit: contain;
        display: none;
        min-height: 0;
    }

    .emiewn-resolution {
        width: 100%;
        text-align: center;
        color: #777;
        font-size: 10px;
        font-family: monospace;
        padding: 4px 0;
        background: #121212;
        border-top: 1px solid #2a2a2a;
        display: none;
    }
`;
document.head.appendChild(style);

app.registerExtension({
    name: "Emiewn.ImgPaste",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === "EmiewnImgPaste") {
            
            const onNodeCreated = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function () {
                const r = onNodeCreated ? onNodeCreated.apply(this, arguments) : undefined;

                const node = this;
                const widget = node.widgets[0];
                widget.type = "hidden"; 

                const div = document.createElement("div");
                div.className = "emiewn-paste-container";
                div.tabIndex = 1; 

                const content = document.createElement("div");
                content.className = "emiewn-paste-content";
                content.innerHTML = `
                    <div class="emiewn-icon">📋</div>
                    <div class="emiewn-text">Click & Press Ctrl+V</div>
                `;
                div.appendChild(content);

                const imgPreview = document.createElement("img");
                imgPreview.className = "emiewn-preview";
                div.appendChild(imgPreview);

                const resolutionDiv = document.createElement("div");
                resolutionDiv.className = "emiewn-resolution";
                div.appendChild(resolutionDiv);

                const resizeNodeToImage = () => {
                    if (!imgPreview.naturalWidth) return;

                    const w = imgPreview.naturalWidth;
                    const h = imgPreview.naturalHeight;
                    const aspectRatio = h / w;

                    resolutionDiv.innerText = `${w}x${h}`;
                    resolutionDiv.style.display = "block";

                    const nodeWidth = node.size[0];
                    
                    const extraHeight = 45; 
                    const targetHeight = (nodeWidth * aspectRatio) + extraHeight;

                    node.setSize([nodeWidth, targetHeight]);
                    app.graph.setDirtyCanvas(true, true);
                };

                imgPreview.onload = () => {
                    content.style.display = "none";
                    imgPreview.style.display = "block";
                    div.style.justifyContent = "space-between";
                    resizeNodeToImage();
                };

                const uploadFile = async (file) => {
                    try {
                        const body = new FormData();
                        body.append("image", file);
                        const resp = await api.fetchApi("/upload/image", { method: "POST", body });

                        if (resp.status === 200) {
                            const data = await resp.json();
                            widget.value = data.name;
                            
                            imgPreview.src = api.apiURL(`/view?filename=${data.name}&type=input&t=${Date.now()}`);
                        } else {
                            alert("Upload failed: " + resp.statusText);
                        }
                    } catch (error) {
                        console.error(error);
                        alert("Error uploading image.");
                    }
                };

                div.addEventListener("paste", (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    
                    const items = (e.clipboardData || e.originalEvent.clipboardData).items;
                    for (let index in items) {
                        const item = items[index];
                        if (item.kind === "file") {
                            uploadFile(item.getAsFile());
                        }
                    }
                });

                div.addEventListener("dragover", (e) => { 
                    e.preventDefault(); e.stopPropagation(); 
                    div.classList.add('focused'); 
                });
                div.addEventListener("dragleave", (e) => { 
                    e.preventDefault(); e.stopPropagation(); 
                    div.classList.remove('focused'); 
                });
                div.addEventListener("drop", (e) => {
                    e.preventDefault(); e.stopPropagation();
                    div.classList.remove('focused');
                    if (e.dataTransfer.files?.[0]) uploadFile(e.dataTransfer.files[0]);
                });

                div.addEventListener("focus", () => div.classList.add('focused'));
                div.addEventListener("blur", () => div.classList.remove('focused'));

                node.addDOMWidget("custom_paste_box", "custom", div, {
                    serialize: false,
                    hideOnZoom: false
                });

                node.setSize([240, 180]);

                return r;
            };
        }
    }
});