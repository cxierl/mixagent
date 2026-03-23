const { app, BrowserWindow, shell, ipcMain } = require('electron');
const { autoUpdater } = require('electron-updater');
const path = require('path');

let mainWindow = null;
let updaterInitialized = false;
let updateAuthToken = (process.env.GH_TOKEN || '').trim();
let updaterState = {
  status: 'idle',
  message: '',
  version: app.getVersion(),
  targetVersion: '',
  progress: 0,
  hasToken: !!updateAuthToken
};
let lastUpdateCheckAt = 0;
let updateCheckInFlight = false;

function sendUpdaterState(patch = {}) {
  updaterState = { ...updaterState, ...patch, hasToken: !!updateAuthToken };
  if (!mainWindow || mainWindow.isDestroyed()) return;
  mainWindow.webContents.send('mix-update-status', updaterState);
}

function applyUpdateToken(token) {
  updateAuthToken = String(token || '').trim();
  autoUpdater.requestHeaders = updateAuthToken
    ? { Authorization: `Bearer ${updateAuthToken}` }
    : {};
  sendUpdaterState();
}

function sanitizeUpdaterError(error) {
  let msg = String(error?.message || error || '更新失败。');
  if (/releases\.atom/i.test(msg) && /\b404\b/.test(msg)) {
    return '更新检查失败：当前仓库为私有仓库，请先配置 GitHub Token（需要 repo 权限）。';
  }
  msg = msg.replace(/Headers:\s*\{[\s\S]*$/i, '');
  msg = msg.replace(/(authorization|cookie|set-cookie)\s*[:=][^,\n]*/gi, '');
  msg = msg.replace(/\s+/g, ' ').trim();
  if (msg.length > 220) msg = `${msg.slice(0, 220)}...`;
  return msg || '更新失败。';
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
      message: sanitizeUpdaterError(error),
      progress: 0
    });
    return { ok: false, reason: 'error', error: sanitizeUpdaterError(error) };
  } finally {
    updateCheckInFlight = false;
  }
}

function setupAutoUpdater() {
  if (updaterInitialized) return;
  updaterInitialized = true;

  autoUpdater.autoDownload = false;
  autoUpdater.autoInstallOnAppQuit = true;
  applyUpdateToken(updateAuthToken);

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
      message: sanitizeUpdaterError(error),
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
ipcMain.handle('mix-update-set-token', async (_event, token = '') => {
  applyUpdateToken(token);
  return { ok: true, hasToken: !!updateAuthToken };
});
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
      message: sanitizeUpdaterError(error),
      progress: 0
    });
    return { ok: false, error: sanitizeUpdaterError(error) };
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
