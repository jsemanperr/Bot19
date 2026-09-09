// main.js - Proceso principal de Electron para el HUD de Kaori
// Ventana simple, siempre-encima opcional, que consume la API local
// de JARVIS (server.py) para mostrar estado y permitir comandos rapidos.

const { app, BrowserWindow } = require("electron");
const path = require("path");

function crearVentana() {
  const ventana = new BrowserWindow({
    width: 420,
    height: 640,
    title: "Kaori HUD",
    backgroundColor: "#0d0f14",
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  ventana.loadFile(path.join(__dirname, "index.html"));
}

app.whenReady().then(() => {
  crearVentana();

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      crearVentana();
    }
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});
