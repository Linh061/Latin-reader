/**
 * Electron main process for Latin Reader.
 * 
 * Starts the Flask backend as a child process and creates the Electron window.
 */

const { app, BrowserWindow } = require('electron');
const { spawn } = require('child_process');
const path = require('path');
const http = require('http');

let mainWindow;
let flaskProcess;

const BACKEND_PORT = 5000;
const FRONTEND_PORT = 3000;
const isDev = !app.isPackaged;

function startFlask() {
  const backendDir = path.join(__dirname, '..', 'backend');
  
  flaskProcess = spawn('python3', ['app.py'], {
    cwd: backendDir,
    env: { ...process.env, FLASK_ENV: isDev ? 'development' : 'production' },
  });

  flaskProcess.stdout.on('data', (data) => {
    console.log(`[Flask] ${data}`);
  });

  flaskProcess.stderr.on('data', (data) => {
    console.error(`[Flask] ${data}`);
  });

  flaskProcess.on('close', (code) => {
    console.log(`[Flask] exited with code ${code}`);
  });
}

function waitForFlask(retries = 30) {
  return new Promise((resolve, reject) => {
    const check = (attempt) => {
      http.get(`http://127.0.0.1:${BACKEND_PORT}/api/health`, (res) => {
        if (res.statusCode === 200) {
          resolve();
        } else if (attempt < retries) {
          setTimeout(() => check(attempt + 1), 1000);
        } else {
          reject(new Error('Flask failed to start'));
        }
      }).on('error', () => {
        if (attempt < retries) {
          setTimeout(() => check(attempt + 1), 1000);
        } else {
          reject(new Error('Flask failed to start'));
        }
      });
    };
    check(0);
  });
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1000,
    minHeight: 600,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
    },
    title: 'Latin Reader',
  });

  if (isDev) {
    mainWindow.loadURL(`http://localhost:${FRONTEND_PORT}`);
    mainWindow.webContents.openDevTools();
  } else {
    // In production, serve the built frontend
    mainWindow.loadFile(path.join(__dirname, '..', 'frontend', 'dist', 'index.html'));
  }

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

app.whenReady().then(async () => {
  startFlask();
  
  try {
    await waitForFlask();
    console.log('Flask backend is ready');
  } catch (e) {
    console.error('Failed to start Flask backend:', e.message);
  }

  createWindow();
});

app.on('window-all-closed', () => {
  if (flaskProcess) {
    flaskProcess.kill();
  }
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('activate', () => {
  if (mainWindow === null) {
    createWindow();
  }
});

app.on('before-quit', () => {
  if (flaskProcess) {
    flaskProcess.kill();
  }
});
