const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('mixDesktop', {
  env: 'desktop',
  minimize: () => ipcRenderer.send('mix-win-control', 'minimize'),
  maximizeToggle: () => ipcRenderer.send('mix-win-control', 'maximize-toggle'),
  close: () => ipcRenderer.send('mix-win-control', 'close'),
  getUpdateState: () => ipcRenderer.invoke('mix-update-get-state'),
  checkForUpdates: (force = true) => ipcRenderer.invoke('mix-update-check', force),
  downloadUpdate: () => ipcRenderer.invoke('mix-update-download'),
  installUpdate: () => ipcRenderer.invoke('mix-update-install'),
  onUpdateStatus: (handler) => {
    if (typeof handler !== 'function') return () => {};
    const wrapped = (_, payload) => handler(payload);
    ipcRenderer.on('mix-update-status', wrapped);
    return () => ipcRenderer.removeListener('mix-update-status', wrapped);
  }
});
