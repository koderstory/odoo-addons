/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ImageField } from "@web/views/fields/image/image_field";

patch(ImageField.prototype, {
    /**
     * Paste handler: reads image from clipboard and feeds it into ImageField upload pipeline.
     */
    async onFilePaste(ev) {
        try {
            const items = ev.clipboardData?.items || [];
            if (!items.length) return;

            for (const item of items) {
                if (item.kind !== "file") continue;
                if (!item.type || !item.type.startsWith("image/")) continue;

                const file = item.getAsFile();
                if (!file) continue;

                const dataURL = await new Promise((resolve, reject) => {
                    const reader = new FileReader();
                    reader.onload = () => resolve(String(reader.result || ""));
                    reader.onerror = (e) => reject(e);
                    reader.readAsDataURL(file);
                });

                // data:image/png;base64,AAAA...
                const base64 = dataURL.includes(",") ? dataURL.split(",")[1] : "";

                // Odoo's ImageField upload handler commonly expects more than just {data}
                const mime = file.type || "image/png";
                const ext = (mime.split("/")[1] || "png").toLowerCase();
                const name = file.name || `clipboard.${ext}`;

                if (typeof this.onFileUploaded !== "function") {
                    console.warn(
                        "[image_field_paste_upload] ImageField.onFileUploaded is not available in this Odoo build."
                    );
                    return;
                }

                // Most compatible payload shape across recent versions:
                await this.onFileUploaded({
                    data: base64,
                    name,
                    type: mime,
                    size: file.size,
                });

                // only handle the first image item
                return;
            }
        } catch (err) {
            console.error("[image_field_paste_upload] Paste failed:", err);
        }
    },

    /**
     * Prevent the contenteditable area from accumulating pasted content.
     */
    cleanPaste(ev) {
        const el = ev.currentTarget || ev.target;
        if (el) {
            el.innerHTML = '<i class="fa fa-copy fa-fw"></i>';
        }
    },

    /**
     * Convenience: click focuses paste target so user can Cmd/Ctrl+V immediately.
     */
    focusPasteTarget(ev) {
        const el = ev.currentTarget || ev.target;
        if (el && typeof el.focus === "function") {
            el.focus();
        }
    },
});
