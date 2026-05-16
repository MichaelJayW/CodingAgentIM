#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');
const os = require('os');

const NOTIF_FILE = path.join(os.homedir(), '.codingagentim', 'notifications.jsonl');
const OFFSET_DIR = path.join(os.homedir(), '.codingagentim', '.notif_offsets');

process.on('uncaughtException', () => process.exit(0));
process.on('unhandledRejection', () => process.exit(0));

function main() {
  if (!fs.existsSync(NOTIF_FILE)) {
    process.exit(0);
  }

  let stat;
  try {
    stat = fs.statSync(NOTIF_FILE);
  } catch {
    process.exit(0);
  }

  const ppid = process.ppid;
  const offsetFile = path.join(OFFSET_DIR, String(ppid));

  let offset = 0;
  try {
    offset = parseInt(fs.readFileSync(offsetFile, 'utf-8'), 10) || 0;
  } catch {}

  if (stat.size <= offset) {
    cleanStaleOffsets();
    process.exit(0);
  }

  // File was truncated/rotated — reset offset
  if (offset > stat.size) {
    offset = 0;
  }

  let newData;
  try {
    const fd = fs.openSync(NOTIF_FILE, 'r');
    const buf = Buffer.alloc(stat.size - offset);
    fs.readSync(fd, buf, 0, buf.length, offset);
    fs.closeSync(fd);
    newData = buf.toString('utf-8').trim();
  } catch {
    process.exit(0);
  }

  if (!newData) {
    process.exit(0);
  }

  // Save new offset before processing
  try {
    fs.mkdirSync(OFFSET_DIR, { recursive: true });
    fs.writeFileSync(offsetFile, String(stat.size));
  } catch {}

  const lines = newData.split('\n').filter(Boolean);
  const notifications = [];
  for (const line of lines) {
    try {
      notifications.push(JSON.parse(line));
    } catch {}
  }

  if (notifications.length === 0) {
    process.exit(0);
  }

  const received = notifications.filter(n => n.type === 'received');
  if (received.length === 0) {
    process.exit(0);
  }

  const summaries = received.map(n => {
    const sender = n.sender || '?';
    const text = (n.text || '').slice(0, 60);
    const chat = n.chat ? `(${n.chat})` : '';
    return `${sender}${chat}: ${text}`;
  });

  process.stderr.write('\n🔔 钉钉新消息:\n' + summaries.map(s => '  ' + s).join('\n') + '\n\n');
  process.stdout.write(JSON.stringify({ dingtalk_new_messages: summaries }));

  // Rotate JSONL if too large (>200KB)
  try {
    if (stat.size > 200 * 1024) {
      const all = fs.readFileSync(NOTIF_FILE, 'utf-8').trim().split('\n');
      const keep = all.slice(-50).join('\n') + '\n';
      fs.writeFileSync(NOTIF_FILE, keep);
    }
  } catch {}
}

function cleanStaleOffsets() {
  try {
    if (!fs.existsSync(OFFSET_DIR)) return;
    const files = fs.readdirSync(OFFSET_DIR);
    for (const f of files) {
      const pid = parseInt(f, 10);
      if (!pid) continue;
      try {
        process.kill(pid, 0);
      } catch {
        // PID doesn't exist — remove stale offset
        try { fs.unlinkSync(path.join(OFFSET_DIR, f)); } catch {}
      }
    }
  } catch {}
}

main();
