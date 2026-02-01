import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import fs from 'fs'
import path from 'path'

// #region agent log
const logPath = '/app/.cursor/debug.log';
const logEntry = (data) => {
  try {
    const logLine = JSON.stringify({
      sessionId: 'debug-session',
      runId: 'run1',
      hypothesisId: data.hypothesisId || 'A',
      location: 'vite.config.js',
      message: data.message,
      data: data.data || {},
      timestamp: Date.now()
    }) + '\n';
    fs.appendFileSync(logPath, logLine);
  } catch (e) {}
};
// #endregion

// In Docker, use service name. In local dev, use localhost
// Docker Compose service name is 'backend'
const backendUrl = process.env.VITE_BACKEND_URL || 'http://backend:8000'

// #region agent log
logEntry({
  hypothesisId: 'A',
  message: 'Vite config loaded - backendUrl determined',
  data: { backendUrl, envVar: process.env.VITE_BACKEND_URL || 'not set' }
});
// #endregion

export default defineConfig({
 plugins: [react()],
 build: {
  minify: process.env.BUILD_MINIFY !== 'false',
 },
 server: {
  port: 5173,
  host: '0.0.0.0',
  proxy: {
   '/auth': {
    target: backendUrl,
    changeOrigin: true,
    secure: false,
    timeout: 30000,
    // #region agent log
    configure: (proxy, options) => {
      proxy.on('error', (err, req, res) => {
        logEntry({
          hypothesisId: 'A',
          message: 'Proxy error on /auth',
          data: { error: err.message, code: err.code, target: options.target }
        });
      });
      proxy.on('proxyReq', (proxyReq, req, res) => {
        logEntry({
          hypothesisId: 'B',
          message: 'Proxy request initiated /auth',
          data: { url: req.url, target: options.target }
        });
      });
      proxy.on('proxyRes', (proxyRes, req, res) => {
        logEntry({
          hypothesisId: 'B',
          message: 'Proxy response received /auth',
          data: { statusCode: proxyRes.statusCode, url: req.url }
        });
      });
    },
    // #endregion
   },
   '/users': {
    target: backendUrl,
    changeOrigin: true,
    secure: false,
    timeout: 30000,
    // #region agent log
    configure: (proxy, options) => {
      proxy.on('error', (err, req, res) => {
        logEntry({
          hypothesisId: 'A',
          message: 'Proxy error on /users',
          data: { error: err.message, code: err.code, target: options.target }
        });
      });
    },
    // #endregion
   },
   '/projects': {
    target: backendUrl,
    changeOrigin: true,
    secure: false,
    timeout: 30000,
    // #region agent log
    configure: (proxy, options) => {
      proxy.on('error', (err, req, res) => {
        logEntry({
          hypothesisId: 'A',
          message: 'Proxy error on /projects',
          data: { error: err.message, code: err.code, target: options.target }
        });
      });
    },
    // #endregion
   },
   '/ai': {
    target: backendUrl,
    changeOrigin: true,
    secure: false,
    timeout: 30000,
    // #region agent log
    configure: (proxy, options) => {
      proxy.on('error', (err, req, res) => {
        logEntry({
          hypothesisId: 'A',
          message: 'Proxy error on /ai',
          data: { error: err.message, code: err.code, target: options.target }
        });
      });
    },
    // #endregion
   },
  }
 }
})
