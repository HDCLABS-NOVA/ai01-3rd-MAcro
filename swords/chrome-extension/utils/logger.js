/**
 * Structured Logger
 */

const LogLevel = {
  DEBUG: 0,
  INFO: 1,
  WARN: 2,
  ERROR: 3
};

class Logger {
  constructor(minLevel = LogLevel.INFO) {
    this.minLevel = minLevel;
    this.logs = [];
    this.maxLogs = 500;
  }

  log(level, event, data = {}) {
    if (level < this.minLevel) return;

    const entry = {
      timestamp: Date.now(),
      time: new Date().toISOString(),
      level: Object.keys(LogLevel)[level],
      event,
      data: {...data}
    };

    this.logs.push(entry);

    // Trim if too large
    if (this.logs.length > this.maxLogs) {
      this.logs = this.logs.slice(-this.maxLogs);
    }

    // Console output with color
    const colors = {
      DEBUG: 'color: #888',
      INFO: 'color: #3498db',
      WARN: 'color: #f39c12',
      ERROR: 'color: #e74c3c; font-weight: bold'
    };

    console.log(
      `%c[${entry.level}] ${event}`,
      colors[entry.level],
      data
    );

    // Send to background for persistence
    this.sendToBackground(entry);
  }

  debug(event, data) {
    this.log(LogLevel.DEBUG, event, data);
  }

  info(event, data) {
    this.log(LogLevel.INFO, event, data);
  }

  warn(event, data) {
    this.log(LogLevel.WARN, event, data);
  }

  error(event, data) {
    this.log(LogLevel.ERROR, event, data);
  }

  sendToBackground(entry) {
    // Check if chrome.runtime is available (not available in MAIN world)
    if (typeof chrome === 'undefined' || !chrome.runtime || !chrome.runtime.sendMessage) {
      return; // Silently skip - we're in MAIN world
    }
    try {
      chrome.runtime.sendMessage({
        type: 'LOG',
        payload: entry
      });
    } catch (e) {
      // Ignore if background not available
    }
  }

  getLogs(filter = {}) {
    let filtered = this.logs;

    if (filter.level) {
      filtered = filtered.filter(log => log.level === filter.level);
    }

    if (filter.event) {
      filtered = filtered.filter(log => log.event.includes(filter.event));
    }

    if (filter.since) {
      filtered = filtered.filter(log => log.timestamp >= filter.since);
    }

    return filtered;
  }

  exportLogs() {
    return JSON.stringify(this.logs, null, 2);
  }

  clear() {
    this.logs = [];
  }

  /**
   * Send complete booking flow logs to server
   * @param {Object} metadata - Metadata about the booking attempt
   * @param {Object} stages - Detailed stage-by-stage data
   * @param {String} customFilename - Optional custom filename (without .json extension)
   */
  async sendToServer(metadata = {}, stages = {}, customFilename = null) {
    try {
      const response = await fetch('http://localhost:8000/api/logs', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          metadata: {
            ...metadata,
            timestamp: new Date().toISOString(),
            url: window.location.href,
            userAgent: navigator.userAgent,
            customFilename  // Pass custom filename to backend
          },
          stages
        })
      });

      if (!response.ok) {
        console.error('Failed to send logs to server:', response.status);
        return false;
      }

      const result = await response.json();
      console.log('✅ Logs sent to server:', result.filename);
      return true;
    } catch (error) {
      console.error('Error sending logs to server:', error);
      return false;
    }
  }
}

// Global logger instance
const logger = new Logger(LogLevel.DEBUG);

// Export
if (typeof window !== 'undefined') {
  window.logger = logger;
  window.LogLevel = LogLevel;
}
