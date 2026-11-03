const http = require('http');
const fs = require('fs');
const path = require('path');

const PORT = 8000;
const HTML_FILE = path.join(__dirname, 'smart_ward_icu_dashboard.html');

let systemArmed = true;
let emergencyActive = false;

const server = http.createServer((req, res) => {
  // CORS Headers
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') {
    res.writeHead(204);
    res.end();
    return;
  }

  // Route 1: Serve Dashboard UI
  if (req.url === '/' || req.url === '/index.html' || req.url.startsWith('/smart_ward_icu_dashboard.html')) {
    fs.readFile(HTML_FILE, (err, content) => {
      if (err) {
        res.writeHead(500, { 'Content-Type': 'text/plain' });
        res.end('Server Error: smart_ward_icu_dashboard.html not found');
        return;
      }
      res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
      res.end(content);
    });
    return;
  }

  // Route 2: Live ESP32 Telemetry Endpoint
  if (req.url.startsWith('/data')) {
    const bpm = emergencyActive 
      ? Math.floor(108 + Math.random() * 14) 
      : Math.floor(72 + Math.random() * 6);

    const payload = {
      bpm: bpm,
      spo2: emergencyActive ? 95 : 98,
      temp: parseFloat((36.8 + (Math.random() * 0.2 - 0.1)).toFixed(1)),
      bp: emergencyActive ? '138/88' : '120/78',
      safetyStatus: emergencyActive ? '🚨 EMERGENCY: FALL DETECTED!' : 'NORMAL - STABLE',
      isEmergency: emergencyActive && systemArmed,
      systemState: systemArmed ? 'ARMED' : 'STANDBY',
      bedOccupied: !emergencyActive,
      accel: {
        x: parseFloat((Math.random() * 0.04 - 0.02).toFixed(2)),
        y: parseFloat((Math.random() * 0.04 - 0.02).toFixed(2)),
        z: emergencyActive ? 3.85 : 0.98
      },
      esp32: {
        connected: true,
        ip: '127.0.0.1:8000',
        rssi: -52,
        uptimeSec: Math.floor(process.uptime()),
        latencyMs: Math.floor(4 + Math.random() * 8)
      }
    };

    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify(payload));
    return;
  }

  // Route 3: Control Endpoint (Armed / Standby)
  if (req.url.startsWith('/control')) {
    const urlObj = new URL(req.url, `http://localhost:${PORT}`);
    const state = urlObj.searchParams.get('state');
    if (state === 'ARMED') systemArmed = true;
    if (state === 'STANDBY') {
      systemArmed = false;
      emergencyActive = false;
    }
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ status: 'ok', systemState: systemArmed ? 'ARMED' : 'STANDBY' }));
    return;
  }

  // 404 Catch-All
  res.writeHead(404, { 'Content-Type': 'text/plain' });
  res.end('Not Found');
});

server.listen(PORT, '0.0.0.0', () => {
  console.log(`Smart Ward ICU Dashboard server listening on http://localhost:${PORT}/`);
});
