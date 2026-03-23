const { app, BrowserWindow, shell, ipcMain } = require('electron');
const { autoUpdater } = require('electron-updater');
const path = require('path');

let mainWindow = null;
let updaterInitialized = false;
let updaterState = {
  status: 'idle',
  message: '',
  version: app.getVersion(),
  targetVersion: '',
  progress: 0
};
let lastUpdateCheckAt = 0;
let updateCheckInFlight = false;

function sendUpdaterState(patch = {}) {
  updaterState = { ...updaterState, ...patch };
  if (!mainWindow || mainWindow.isDestroyed()) return;
  mainWindow.webContents.send('mix-update-status', updaterState);
}

function canCheckUpdates(force = false) {
  if (!app.isPackaged) return force;
  if (updateCheckInFlight && !force) return false;
  const now = Date.now();
  if (!force && now - lastUpdateCheckAt < 10 * 60 * 1000) return false;
  lastUpdateCheckAt = now;
  return true;
}

async function checkForUpdates(force = false) {
  if (!app.isPackaged) {
    sendUpdaterState({
      status: 'idle',
      message: '开发环境不检查自动更新。',
      targetVersion: '',
      progress: 0
    });
    return { ok: false, reason: 'dev' };
  }
  if (!canCheckUpdates(force)) return { ok: false, reason: 'throttled' };
  try {
    updateCheckInFlight = true;
    sendUpdaterState({
      status: 'checking',
      message: '正在检查新版本…',
      targetVersion: '',
      progress: 0
    });
    await autoUpdater.checkForUpdates();
    return { ok: true };
  } catch (error) {
    sendUpdaterState({
      status: 'error',
      message: error?.message || '检查更新失败。',
      progress: 0
    });
    return { ok: false, reason: 'error', error: error?.message || String(error) };
  } finally {
    updateCheckInFlight = false;
  }
}

function setupAutoUpdater() {
  if (updaterInitialized) return;
  updaterInitialized = true;

  autoUpdater.autoDownload = false;
  autoUpdater.autoInstallOnAppQuit = true;

  autoUpdater.on('checking-for-update', () => {
    sendUpdaterState({
      status: 'checking',
      message: '正在检查新版本…',
      progress: 0
    });
  });

  autoUpdater.on('update-available', (info) => {
    sendUpdaterState({
      status: 'available',
      message: `发现新版本 ${info?.version || ''}。`,
      targetVersion: info?.version || '',
      progress: 0
    });
  });

  autoUpdater.on('update-not-available', () => {
    sendUpdaterState({
      status: 'idle',
      message: '',
      targetVersion: '',
      progress: 0
    });
  });

  autoUpdater.on('error', (error) => {
    sendUpdaterState({
      status: 'error',
      message: error?.message || '更新失败。',
      progress: 0
    });
  });

  autoUpdater.on('download-progress', (progress) => {
    sendUpdaterState({
      status: 'downloading',
      message: `正在下载更新 ${Math.round(progress?.percent || 0)}%`,
      progress: Math.max(0, Math.min(100, Math.round(progress?.percent || 0)))
    });
  });

  autoUpdater.on('update-downloaded', (info) => {
    sendUpdaterState({
      status: 'downloaded',
      message: `新版本 ${info?.version || ''} 已下载完成。`,
      targetVersion: info?.version || updaterState.targetVersion || '',
      progress: 100
    });
  });
}

function createWindow() {
  const win = new BrowserWindow({
    width: 1600,
    height: 980,
    minWidth: 1100,
    minHeight: 720,
    backgroundColor: '#0f1726',
    frame: false,
    titleBarStyle: 'hidden',
    titleBarOverlay: false,
    autoHideMenuBar: true,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true
    }
  });

  mainWindow = win;
  win.loadFile(path.join(__dirname, '..', 'index.html'));

  win.webContents.on('did-finish-load', () => {
    sendUpdaterState();
    setTimeout(() => { checkForUpdates(false); }, 1800);
  });

  win.on('focus', () => {
    checkForUpdates(false);
  });

  win.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: 'deny' };
  });
}

ipcMain.on('mix-win-control', (event, action) => {
  const win = BrowserWindow.fromWebContents(event.sender);
  if (!win) return;
  if (action === 'minimize') win.minimize();
  else if (action === 'maximize-toggle') {
    if (win.isMaximized()) win.unmaximize();
    else win.maximize();
  } else if (action === 'close') win.close();
});

ipcMain.handle('mix-update-get-state', async () => updaterState);
ipcMain.handle('mix-update-check', async (_event, force = true) => checkForUpdates(Boolean(force)));
ipcMain.handle('mix-update-download', async () => {
  if (!app.isPackaged) return { ok: false, reason: 'dev' };
  try {
    sendUpdaterState({
      status: 'downloading',
      message: '正在准备下载更新…',
      progress: 0
    });
    await autoUpdater.downloadUpdate();
    return { ok: true };
  } catch (error) {
    sendUpdaterState({
      status: 'error',
      message: error?.message || '下载更新失败。',
      progress: 0
    });
    return { ok: false, error: error?.message || String(error) };
  }
});
ipcMain.handle('mix-update-install', async () => {
  if (!app.isPackaged) return { ok: false, reason: 'dev' };
  setImmediate(() => autoUpdater.quitAndInstall(false, true));
  return { ok: true };
});

app.whenReady().then(() => {
  setupAutoUpdater();
  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});
