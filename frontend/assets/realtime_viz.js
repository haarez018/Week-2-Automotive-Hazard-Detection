// realtime_viz.js (FINAL WORKING VERSION)

// ✅ WebSocket URL to backend
const WS_URL = "ws://127.0.0.1:8000/ws/video";

// ✅ Canvas setup
const canvas = document.getElementById("liveCanvas");
const ctx = canvas.getContext("2d");

// Buffer image for decoded JPEG frames
const img = new Image();

/* ------------------------------------------------------
   ✅ Draw JPEG frame onto canvas
------------------------------------------------------ */
function drawFrame(arrayBuffer) {
    const blob = new Blob([arrayBuffer], { type: "image/jpeg" });
    const url = URL.createObjectURL(blob);

    img.onload = () => {
        ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
        URL.revokeObjectURL(url);
    };

    img.src = url;
}

/* ------------------------------------------------------
   ✅ Handle hazard JSON (logs only for now)
------------------------------------------------------ */
function handleHazardJSON(text) {
    try {
        const data = JSON.parse(text);
        console.log("⚠️ Hazard:", data);
    } catch {
        console.log("Received non-JSON text:", text);
    }
}

let socket = null;

/* ------------------------------------------------------
   ✅ Connect WebSocket
------------------------------------------------------ */
function connectWebSocket() {
    console.log("Connecting to WebSocket:", WS_URL);

    socket = new WebSocket(WS_URL);
    socket.binaryType = "arraybuffer";   // ✅ CRITICAL FIX

    socket.onopen = () => {
        console.log("✅ WebSocket Connected");
    };

    socket.onmessage = (event) => {
        if (event.data instanceof ArrayBuffer) {
            // ✅ Binary data → JPEG frame
            drawFrame(event.data);
        } else {
            // ✅ Text → JSON hazard log
            handleHazardJSON(event.data);
        }
    };

    socket.onclose = () => {
        console.log("❌ WebSocket Closed — retrying in 2s...");
        setTimeout(connectWebSocket, 2000);
    };

    socket.onerror = (err) => {
        console.log("WebSocket Error:", err);
    };
}

/* ------------------------------------------------------
   ✅ Start WebSocket when page loads
------------------------------------------------------ */
document.addEventListener("DOMContentLoaded", connectWebSocket);
