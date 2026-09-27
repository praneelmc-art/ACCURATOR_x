const express = require('express');
const http = require('http');
const { Server } = require('socket.io');
const { SerialPort } = require('serialport');
const { ReadlineParser } = require('@serialport/parser-readline');

const app = express();
const server = http.createServer(app);
const io = new Server(server);

// Serve static files from the 'public' folder
app.use(express.static('public'));

// Arduino USB COM Port (detected on COM11)
const portName = process.env.SERIAL_PORT || 'COM11'; 
const baudRate = 9600;

const serialPort = new SerialPort({ path: portName, baudRate: baudRate });
const parser = serialPort.pipe(new ReadlineParser({ delimiter: '\r\n' }));

serialPort.on('open', () => {
  console.log(`[SERIAL] Connected to Arduino on port ${portName}`);
});

serialPort.on('error', (err) => {
  console.error('[SERIAL ERROR]: ', err.message);
});

// When a line is read from Arduino, broadcast it to all connected browser clients
parser.on('data', (data) => {
  console.log(`[ARDUINO]: ${data}`);

  let rawValue = null;
  let calValue = null;
  let ldr = null;
  let packetId = null;

  const rawMatch = data.match(/RawH?:\s*([0-9.-]+)/i);
  if (rawMatch) rawValue = parseFloat(rawMatch[1]);

  const calMatch = data.match(/CalH?:\s*([0-9.-]+)/i);
  if (calMatch) calValue = parseFloat(calMatch[1]);

  const ldrMatch = data.match(/LDR:\s*([0-9.-]+)/i);
  if (ldrMatch) ldr = parseFloat(ldrMatch[1]);

  const idMatch = data.match(/ID:\s*([0-9]+)/i);
  if (idMatch) packetId = parseInt(idMatch[1]);

  io.emit('sensor-data', {
    raw: data,
    timestamp: new Date().toLocaleTimeString(),
    rawValue,
    calValue,
    ldr,
    packetId
  });
});

const PORT = 3000;
server.listen(PORT, () => {
  console.log(`[SERVER] Dashboard running at http://localhost:${PORT}`);
});