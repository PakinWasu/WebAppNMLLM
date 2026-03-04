// vite.config.js
import { defineConfig } from "file:///D:/0.Project%20End/WebAppNMLLM/frontend/node_modules/vite/dist/node/index.js";
import react from "file:///D:/0.Project%20End/WebAppNMLLM/frontend/node_modules/@vitejs/plugin-react/dist/index.js";
import fs from "fs";
var logPath = "/app/.cursor/debug.log";
var logEntry = (data) => {
  try {
    const logLine = JSON.stringify({
      sessionId: "debug-session",
      runId: "run1",
      hypothesisId: data.hypothesisId || "A",
      location: "vite.config.js",
      message: data.message,
      data: data.data || {},
      timestamp: Date.now()
    }) + "\n";
    fs.appendFileSync(logPath, logLine);
  } catch (e) {
  }
};
var backendUrl = process.env.VITE_BACKEND_URL || "http://backend:8000";
logEntry({
  hypothesisId: "A",
  message: "Vite config loaded - backendUrl determined",
  data: { backendUrl, envVar: process.env.VITE_BACKEND_URL || "not set" }
});
var vite_config_default = defineConfig({
  plugins: [react()],
  build: {
    minify: process.env.BUILD_MINIFY !== "false"
  },
  server: {
    port: 5173,
    host: "0.0.0.0",
    proxy: {
      "/auth": {
        target: backendUrl,
        changeOrigin: true,
        secure: false,
        timeout: 3e4,
        // #region agent log
        configure: (proxy, options) => {
          proxy.on("error", (err, req, res) => {
            logEntry({
              hypothesisId: "A",
              message: "Proxy error on /auth",
              data: { error: err.message, code: err.code, target: options.target }
            });
          });
          proxy.on("proxyReq", (proxyReq, req, res) => {
            logEntry({
              hypothesisId: "B",
              message: "Proxy request initiated /auth",
              data: { url: req.url, target: options.target }
            });
          });
          proxy.on("proxyRes", (proxyRes, req, res) => {
            logEntry({
              hypothesisId: "B",
              message: "Proxy response received /auth",
              data: { statusCode: proxyRes.statusCode, url: req.url }
            });
          });
        }
        // #endregion
      },
      "/users": {
        target: backendUrl,
        changeOrigin: true,
        secure: false,
        timeout: 3e4,
        // #region agent log
        configure: (proxy, options) => {
          proxy.on("error", (err, req, res) => {
            logEntry({
              hypothesisId: "A",
              message: "Proxy error on /users",
              data: { error: err.message, code: err.code, target: options.target }
            });
          });
        }
        // #endregion
      },
      "/projects": {
        target: backendUrl,
        changeOrigin: true,
        secure: false,
        timeout: 3e4,
        // #region agent log
        configure: (proxy, options) => {
          proxy.on("error", (err, req, res) => {
            logEntry({
              hypothesisId: "A",
              message: "Proxy error on /projects",
              data: { error: err.message, code: err.code, target: options.target }
            });
          });
        }
        // #endregion
      },
      "/ai": {
        target: backendUrl,
        changeOrigin: true,
        secure: false,
        timeout: 3e4,
        // #region agent log
        configure: (proxy, options) => {
          proxy.on("error", (err, req, res) => {
            logEntry({
              hypothesisId: "A",
              message: "Proxy error on /ai",
              data: { error: err.message, code: err.code, target: options.target }
            });
          });
        }
        // #endregion
      }
    }
  }
});
export {
  vite_config_default as default
};
//# sourceMappingURL=data:application/json;base64,ewogICJ2ZXJzaW9uIjogMywKICAic291cmNlcyI6IFsidml0ZS5jb25maWcuanMiXSwKICAic291cmNlc0NvbnRlbnQiOiBbImNvbnN0IF9fdml0ZV9pbmplY3RlZF9vcmlnaW5hbF9kaXJuYW1lID0gXCJEOlxcXFwwLlByb2plY3QgRW5kXFxcXFdlYkFwcE5NTExNXFxcXGZyb250ZW5kXCI7Y29uc3QgX192aXRlX2luamVjdGVkX29yaWdpbmFsX2ZpbGVuYW1lID0gXCJEOlxcXFwwLlByb2plY3QgRW5kXFxcXFdlYkFwcE5NTExNXFxcXGZyb250ZW5kXFxcXHZpdGUuY29uZmlnLmpzXCI7Y29uc3QgX192aXRlX2luamVjdGVkX29yaWdpbmFsX2ltcG9ydF9tZXRhX3VybCA9IFwiZmlsZTovLy9EOi8wLlByb2plY3QlMjBFbmQvV2ViQXBwTk1MTE0vZnJvbnRlbmQvdml0ZS5jb25maWcuanNcIjtpbXBvcnQgeyBkZWZpbmVDb25maWcgfSBmcm9tICd2aXRlJ1xyXG5pbXBvcnQgcmVhY3QgZnJvbSAnQHZpdGVqcy9wbHVnaW4tcmVhY3QnXHJcbmltcG9ydCBmcyBmcm9tICdmcydcclxuaW1wb3J0IHBhdGggZnJvbSAncGF0aCdcclxuXHJcbi8vICNyZWdpb24gYWdlbnQgbG9nXHJcbmNvbnN0IGxvZ1BhdGggPSAnL2FwcC8uY3Vyc29yL2RlYnVnLmxvZyc7XHJcbmNvbnN0IGxvZ0VudHJ5ID0gKGRhdGEpID0+IHtcclxuICB0cnkge1xyXG4gICAgY29uc3QgbG9nTGluZSA9IEpTT04uc3RyaW5naWZ5KHtcclxuICAgICAgc2Vzc2lvbklkOiAnZGVidWctc2Vzc2lvbicsXHJcbiAgICAgIHJ1bklkOiAncnVuMScsXHJcbiAgICAgIGh5cG90aGVzaXNJZDogZGF0YS5oeXBvdGhlc2lzSWQgfHwgJ0EnLFxyXG4gICAgICBsb2NhdGlvbjogJ3ZpdGUuY29uZmlnLmpzJyxcclxuICAgICAgbWVzc2FnZTogZGF0YS5tZXNzYWdlLFxyXG4gICAgICBkYXRhOiBkYXRhLmRhdGEgfHwge30sXHJcbiAgICAgIHRpbWVzdGFtcDogRGF0ZS5ub3coKVxyXG4gICAgfSkgKyAnXFxuJztcclxuICAgIGZzLmFwcGVuZEZpbGVTeW5jKGxvZ1BhdGgsIGxvZ0xpbmUpO1xyXG4gIH0gY2F0Y2ggKGUpIHt9XHJcbn07XHJcbi8vICNlbmRyZWdpb25cclxuXHJcbi8vIEluIERvY2tlciwgdXNlIHNlcnZpY2UgbmFtZS4gSW4gbG9jYWwgZGV2LCB1c2UgbG9jYWxob3N0XHJcbi8vIERvY2tlciBDb21wb3NlIHNlcnZpY2UgbmFtZSBpcyAnYmFja2VuZCdcclxuY29uc3QgYmFja2VuZFVybCA9IHByb2Nlc3MuZW52LlZJVEVfQkFDS0VORF9VUkwgfHwgJ2h0dHA6Ly9iYWNrZW5kOjgwMDAnXHJcblxyXG4vLyAjcmVnaW9uIGFnZW50IGxvZ1xyXG5sb2dFbnRyeSh7XHJcbiAgaHlwb3RoZXNpc0lkOiAnQScsXHJcbiAgbWVzc2FnZTogJ1ZpdGUgY29uZmlnIGxvYWRlZCAtIGJhY2tlbmRVcmwgZGV0ZXJtaW5lZCcsXHJcbiAgZGF0YTogeyBiYWNrZW5kVXJsLCBlbnZWYXI6IHByb2Nlc3MuZW52LlZJVEVfQkFDS0VORF9VUkwgfHwgJ25vdCBzZXQnIH1cclxufSk7XHJcbi8vICNlbmRyZWdpb25cclxuXHJcbmV4cG9ydCBkZWZhdWx0IGRlZmluZUNvbmZpZyh7XHJcbiBwbHVnaW5zOiBbcmVhY3QoKV0sXHJcbiBidWlsZDoge1xyXG4gIG1pbmlmeTogcHJvY2Vzcy5lbnYuQlVJTERfTUlOSUZZICE9PSAnZmFsc2UnLFxyXG4gfSxcclxuIHNlcnZlcjoge1xyXG4gIHBvcnQ6IDUxNzMsXHJcbiAgaG9zdDogJzAuMC4wLjAnLFxyXG4gIHByb3h5OiB7XHJcbiAgICcvYXV0aCc6IHtcclxuICAgIHRhcmdldDogYmFja2VuZFVybCxcclxuICAgIGNoYW5nZU9yaWdpbjogdHJ1ZSxcclxuICAgIHNlY3VyZTogZmFsc2UsXHJcbiAgICB0aW1lb3V0OiAzMDAwMCxcclxuICAgIC8vICNyZWdpb24gYWdlbnQgbG9nXHJcbiAgICBjb25maWd1cmU6IChwcm94eSwgb3B0aW9ucykgPT4ge1xyXG4gICAgICBwcm94eS5vbignZXJyb3InLCAoZXJyLCByZXEsIHJlcykgPT4ge1xyXG4gICAgICAgIGxvZ0VudHJ5KHtcclxuICAgICAgICAgIGh5cG90aGVzaXNJZDogJ0EnLFxyXG4gICAgICAgICAgbWVzc2FnZTogJ1Byb3h5IGVycm9yIG9uIC9hdXRoJyxcclxuICAgICAgICAgIGRhdGE6IHsgZXJyb3I6IGVyci5tZXNzYWdlLCBjb2RlOiBlcnIuY29kZSwgdGFyZ2V0OiBvcHRpb25zLnRhcmdldCB9XHJcbiAgICAgICAgfSk7XHJcbiAgICAgIH0pO1xyXG4gICAgICBwcm94eS5vbigncHJveHlSZXEnLCAocHJveHlSZXEsIHJlcSwgcmVzKSA9PiB7XHJcbiAgICAgICAgbG9nRW50cnkoe1xyXG4gICAgICAgICAgaHlwb3RoZXNpc0lkOiAnQicsXHJcbiAgICAgICAgICBtZXNzYWdlOiAnUHJveHkgcmVxdWVzdCBpbml0aWF0ZWQgL2F1dGgnLFxyXG4gICAgICAgICAgZGF0YTogeyB1cmw6IHJlcS51cmwsIHRhcmdldDogb3B0aW9ucy50YXJnZXQgfVxyXG4gICAgICAgIH0pO1xyXG4gICAgICB9KTtcclxuICAgICAgcHJveHkub24oJ3Byb3h5UmVzJywgKHByb3h5UmVzLCByZXEsIHJlcykgPT4ge1xyXG4gICAgICAgIGxvZ0VudHJ5KHtcclxuICAgICAgICAgIGh5cG90aGVzaXNJZDogJ0InLFxyXG4gICAgICAgICAgbWVzc2FnZTogJ1Byb3h5IHJlc3BvbnNlIHJlY2VpdmVkIC9hdXRoJyxcclxuICAgICAgICAgIGRhdGE6IHsgc3RhdHVzQ29kZTogcHJveHlSZXMuc3RhdHVzQ29kZSwgdXJsOiByZXEudXJsIH1cclxuICAgICAgICB9KTtcclxuICAgICAgfSk7XHJcbiAgICB9LFxyXG4gICAgLy8gI2VuZHJlZ2lvblxyXG4gICB9LFxyXG4gICAnL3VzZXJzJzoge1xyXG4gICAgdGFyZ2V0OiBiYWNrZW5kVXJsLFxyXG4gICAgY2hhbmdlT3JpZ2luOiB0cnVlLFxyXG4gICAgc2VjdXJlOiBmYWxzZSxcclxuICAgIHRpbWVvdXQ6IDMwMDAwLFxyXG4gICAgLy8gI3JlZ2lvbiBhZ2VudCBsb2dcclxuICAgIGNvbmZpZ3VyZTogKHByb3h5LCBvcHRpb25zKSA9PiB7XHJcbiAgICAgIHByb3h5Lm9uKCdlcnJvcicsIChlcnIsIHJlcSwgcmVzKSA9PiB7XHJcbiAgICAgICAgbG9nRW50cnkoe1xyXG4gICAgICAgICAgaHlwb3RoZXNpc0lkOiAnQScsXHJcbiAgICAgICAgICBtZXNzYWdlOiAnUHJveHkgZXJyb3Igb24gL3VzZXJzJyxcclxuICAgICAgICAgIGRhdGE6IHsgZXJyb3I6IGVyci5tZXNzYWdlLCBjb2RlOiBlcnIuY29kZSwgdGFyZ2V0OiBvcHRpb25zLnRhcmdldCB9XHJcbiAgICAgICAgfSk7XHJcbiAgICAgIH0pO1xyXG4gICAgfSxcclxuICAgIC8vICNlbmRyZWdpb25cclxuICAgfSxcclxuICAgJy9wcm9qZWN0cyc6IHtcclxuICAgIHRhcmdldDogYmFja2VuZFVybCxcclxuICAgIGNoYW5nZU9yaWdpbjogdHJ1ZSxcclxuICAgIHNlY3VyZTogZmFsc2UsXHJcbiAgICB0aW1lb3V0OiAzMDAwMCxcclxuICAgIC8vICNyZWdpb24gYWdlbnQgbG9nXHJcbiAgICBjb25maWd1cmU6IChwcm94eSwgb3B0aW9ucykgPT4ge1xyXG4gICAgICBwcm94eS5vbignZXJyb3InLCAoZXJyLCByZXEsIHJlcykgPT4ge1xyXG4gICAgICAgIGxvZ0VudHJ5KHtcclxuICAgICAgICAgIGh5cG90aGVzaXNJZDogJ0EnLFxyXG4gICAgICAgICAgbWVzc2FnZTogJ1Byb3h5IGVycm9yIG9uIC9wcm9qZWN0cycsXHJcbiAgICAgICAgICBkYXRhOiB7IGVycm9yOiBlcnIubWVzc2FnZSwgY29kZTogZXJyLmNvZGUsIHRhcmdldDogb3B0aW9ucy50YXJnZXQgfVxyXG4gICAgICAgIH0pO1xyXG4gICAgICB9KTtcclxuICAgIH0sXHJcbiAgICAvLyAjZW5kcmVnaW9uXHJcbiAgIH0sXHJcbiAgICcvYWknOiB7XHJcbiAgICB0YXJnZXQ6IGJhY2tlbmRVcmwsXHJcbiAgICBjaGFuZ2VPcmlnaW46IHRydWUsXHJcbiAgICBzZWN1cmU6IGZhbHNlLFxyXG4gICAgdGltZW91dDogMzAwMDAsXHJcbiAgICAvLyAjcmVnaW9uIGFnZW50IGxvZ1xyXG4gICAgY29uZmlndXJlOiAocHJveHksIG9wdGlvbnMpID0+IHtcclxuICAgICAgcHJveHkub24oJ2Vycm9yJywgKGVyciwgcmVxLCByZXMpID0+IHtcclxuICAgICAgICBsb2dFbnRyeSh7XHJcbiAgICAgICAgICBoeXBvdGhlc2lzSWQ6ICdBJyxcclxuICAgICAgICAgIG1lc3NhZ2U6ICdQcm94eSBlcnJvciBvbiAvYWknLFxyXG4gICAgICAgICAgZGF0YTogeyBlcnJvcjogZXJyLm1lc3NhZ2UsIGNvZGU6IGVyci5jb2RlLCB0YXJnZXQ6IG9wdGlvbnMudGFyZ2V0IH1cclxuICAgICAgICB9KTtcclxuICAgICAgfSk7XHJcbiAgICB9LFxyXG4gICAgLy8gI2VuZHJlZ2lvblxyXG4gICB9LFxyXG4gIH1cclxuIH1cclxufSlcclxuIl0sCiAgIm1hcHBpbmdzIjogIjtBQUEyUyxTQUFTLG9CQUFvQjtBQUN4VSxPQUFPLFdBQVc7QUFDbEIsT0FBTyxRQUFRO0FBSWYsSUFBTSxVQUFVO0FBQ2hCLElBQU0sV0FBVyxDQUFDLFNBQVM7QUFDekIsTUFBSTtBQUNGLFVBQU0sVUFBVSxLQUFLLFVBQVU7QUFBQSxNQUM3QixXQUFXO0FBQUEsTUFDWCxPQUFPO0FBQUEsTUFDUCxjQUFjLEtBQUssZ0JBQWdCO0FBQUEsTUFDbkMsVUFBVTtBQUFBLE1BQ1YsU0FBUyxLQUFLO0FBQUEsTUFDZCxNQUFNLEtBQUssUUFBUSxDQUFDO0FBQUEsTUFDcEIsV0FBVyxLQUFLLElBQUk7QUFBQSxJQUN0QixDQUFDLElBQUk7QUFDTCxPQUFHLGVBQWUsU0FBUyxPQUFPO0FBQUEsRUFDcEMsU0FBUyxHQUFHO0FBQUEsRUFBQztBQUNmO0FBS0EsSUFB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
