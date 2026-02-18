/**
 * Message Formatting Utilities
 * Formats JSON message payloads into readable, structured displays
 */

/**
 * Format message payload into readable HTML structure (not JSON)
 */
function formatMessagePayload(payload) {
    if (!payload || typeof payload !== 'object') {
        return '<div class="message-empty">No payload data</div>';
    }

    let html = '<div class="message-payload-formatted">';
    
    // Handle common message fields in a structured way
    if (payload.temperature !== undefined) {
        html += `<div class="payload-row">
            <span class="payload-label">🌡️ Temperature:</span>
            <span class="payload-value">${payload.temperature}°C</span>
        </div>`;
    }
    
    if (payload.humidity !== undefined) {
        html += `<div class="payload-row">
            <span class="payload-label">💧 Humidity:</span>
            <span class="payload-value">${payload.humidity}%</span>
        </div>`;
    }
    
    if (payload.battery !== undefined || payload.battery_level !== undefined) {
        const battery = payload.battery || payload.battery_level;
        const batteryClass = battery > 50 ? 'value-good' : battery > 20 ? 'value-warning' : 'value-danger';
        html += `<div class="payload-row">
            <span class="payload-label">🔋 Battery:</span>
            <span class="payload-value ${batteryClass}">${battery}%</span>
        </div>`;
    }
    
    if (payload.status) {
        const statusClass = payload.status.toLowerCase() === 'ok' || payload.status.toLowerCase() === 'normal' 
            ? 'value-good' 
            : payload.status.toLowerCase() === 'warning' 
            ? 'value-warning' 
            : 'value-danger';
        html += `<div class="payload-row">
            <span class="payload-label">📊 Status:</span>
            <span class="payload-value ${statusClass}">${payload.status}</span>
        </div>`;
    }
    
    if (payload.message || payload.text || payload.msg) {
        const messageText = payload.message || payload.text || payload.msg;
        html += `<div class="payload-row payload-row-full">
            <span class="payload-label">💬 Message:</span>
            <div class="payload-message">${escapeHtml(messageText)}</div>
        </div>`;
    }
    
    if (payload.location || payload.position || (payload.latitude && payload.longitude)) {
        let lat, lon;
        if (payload.location) {
            lat = payload.location.latitude || payload.location.lat;
            lon = payload.location.longitude || payload.location.lon || payload.location.lng;
        } else if (payload.position) {
            lat = payload.position.latitude || payload.position.lat;
            lon = payload.position.longitude || payload.position.lon || payload.position.lng;
        } else {
            lat = payload.latitude || payload.lat;
            lon = payload.longitude || payload.lon || payload.lng;
        }
        
        if (lat !== undefined && lon !== undefined) {
            html += `<div class="payload-row">
                <span class="payload-label">📍 Location:</span>
                <span class="payload-value">${lat.toFixed(6)}, ${lon.toFixed(6)}</span>
            </div>`;
        }
    }
    
    if (payload.nid || payload.network_id) {
        const nid = payload.nid || payload.network_id;
        html += `<div class="payload-row">
            <span class="payload-label">🌐 Network ID:</span>
            <span class="payload-value">${nid}</span>
        </div>`;
    }
    
    if (payload.type) {
        const typeIcon = getMessageTypeIcon(payload.type);
        html += `<div class="payload-row">
            <span class="payload-label">📝 Type:</span>
            <span class="payload-value">${typeIcon} ${payload.type.toUpperCase()}</span>
        </div>`;
    }
    
    if (payload.timestamp || payload.time) {
        const timestamp = payload.timestamp || payload.time;
        try {
            const date = new Date(timestamp);
            const formatted = date.toLocaleString();
            html += `<div class="payload-row">
                <span class="payload-label">🕐 Time:</span>
                <span class="payload-value">${formatted}</span>
            </div>`;
        } catch (e) {
            html += `<div class="payload-row">
                <span class="payload-label">🕐 Time:</span>
                <span class="payload-value">${timestamp}</span>
            </div>`;
        }
    }
    
    // Handle other fields generically
    const commonFields = ['temperature', 'humidity', 'battery', 'battery_level', 'status', 'message', 'text', 'msg', 
                         'location', 'position', 'latitude', 'longitude', 'lat', 'lon', 'lng', 'nid', 'network_id', 
                         'type', 'timestamp', 'time'];
    
    let hasOtherFields = false;
    let otherFieldsHtml = '';
    
    for (const [key, value] of Object.entries(payload)) {
        if (!commonFields.includes(key.toLowerCase()) && value !== null && value !== undefined) {
            hasOtherFields = true;
            const displayValue = typeof value === 'object' 
                ? JSON.stringify(value, null, 2) 
                : String(value);
            
            otherFieldsHtml += `<div class="payload-row">
                <span class="payload-label">${escapeHtml(key)}:</span>
                <span class="payload-value">${escapeHtml(displayValue)}</span>
            </div>`;
        }
    }
    
    if (hasOtherFields) {
        html += '<div class="payload-section-divider"></div>';
        html += '<div class="payload-section-title">Additional Data:</div>';
        html += otherFieldsHtml;
    }
    
    // If no structured fields found, show formatted JSON as fallback
    if (!html.includes('payload-row')) {
        html += '<div class="payload-raw">';
        html += '<pre class="payload-json">' + escapeHtml(JSON.stringify(payload, null, 2)) + '</pre>';
        html += '<button class="btn-copy-json" onclick="copyJSON(this)" data-json=\'' + escapeHtml(JSON.stringify(payload)) + '\'>📋 Copy JSON</button>';
        html += '</div>';
    }
    
    html += '</div>';
    return html;
}

/**
 * Format message routing information
 */
function formatRoutingInfo(message, inboxEntry) {
    let html = '<div class="routing-info">';
    
    if (message.source_device_hid || (message.source_device && message.source_device.hid)) {
        const sourceHid = message.source_device_hid || message.source_device.hid;
        html += `<div class="routing-row">
            <span class="routing-label">📤 Source Device:</span>
            <span class="routing-value">${sourceHid}</span>
        </div>`;
    }
    
    if (inboxEntry && inboxEntry.device_hid) {
        html += `<div class="routing-row">
            <span class="routing-label">📥 Target Device:</span>
            <span class="routing-value">${inboxEntry.device_hid}</span>
        </div>`;
    }
    
    if (inboxEntry && inboxEntry.status) {
        const statusClass = inboxEntry.status === 'acknowledged' ? 'status-success' 
                          : inboxEntry.status === 'pending' ? 'status-warning' 
                          : 'status-danger';
        html += `<div class="routing-row">
            <span class="routing-label">📋 Status:</span>
            <span class="routing-value ${statusClass}">${inboxEntry.status.toUpperCase()}</span>
        </div>`;
    }
    
    if (inboxEntry && inboxEntry.delivery_attempts !== undefined) {
        html += `<div class="routing-row">
            <span class="routing-label">🔄 Delivery Attempts:</span>
            <span class="routing-value">${inboxEntry.delivery_attempts}</span>
        </div>`;
    }
    
    html += '</div>';
    return html;
}

/**
 * Get icon for message type
 */
function getMessageTypeIcon(type) {
    const typeMap = {
        'sensor': '📡',
        'panic': '🚨',
        'ns-panic': '⚠️',
        'ns_panic': '⚠️',
        'unknown': '❓',
        'distress': '🆘',
        'pa': '📢',
        'pm': '🔊',
        'service': '🔧',
        'alert': '📢',
        'alarm': '🚨'
    };
    
    const lowerType = String(type).toLowerCase();
    return typeMap[lowerType] || '📨';
}

/**
 * Format timestamp for display
 */
function formatTimestamp(timestamp) {
    if (!timestamp) return 'No timestamp';
    
    try {
        const date = new Date(timestamp);
        const now = new Date();
        const diffMs = now - date;
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMs / 3600000);
        const diffDays = Math.floor(diffMs / 86400000);
        
        if (diffMins < 1) {
            return 'Just now';
        } else if (diffMins < 60) {
            return `${diffMins} minute${diffMins !== 1 ? 's' : ''} ago`;
        } else if (diffHours < 24) {
            return `${diffHours} hour${diffHours !== 1 ? 's' : ''} ago`;
        } else if (diffDays < 7) {
            return `${diffDays} day${diffDays !== 1 ? 's' : ''} ago`;
        } else {
            return date.toLocaleDateString('en-US', {
                month: 'short',
                day: 'numeric',
                year: date.getFullYear() !== now.getFullYear() ? 'numeric' : undefined
            }) + ' at ' + date.toLocaleTimeString('en-US', {
                hour: '2-digit',
                minute: '2-digit',
                hour12: true
            });
        }
    } catch (e) {
        return String(timestamp);
    }
}

/**
 * Format alert/alarm type for display
 */
function formatMessageSubType(message) {
    if (message.type === 'alarm' && message.alarm_type) {
        const typeMap = {
            'pa': 'Public Address',
            'pm': 'Private Message',
            'service': 'Service Alert'
        };
        return typeMap[message.alarm_type.toLowerCase()] || message.alarm_type.toUpperCase();
    } else if (message.type === 'alert' && message.alert_type) {
        const typeMap = {
            'sensor': 'Sensor Data',
            'panic': 'Panic Alert',
            'ns_panic': 'Non-Silent Panic',
            'ns-panic': 'Non-Silent Panic',
            'unknown': 'Unknown',
            'distress': 'Distress Signal'
        };
        return typeMap[message.alert_type.toLowerCase()] || message.alert_type.toUpperCase();
    }
    return message.type ? message.type.toUpperCase() : 'Unknown';
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    if (text === null || text === undefined) return '';
    const div = document.createElement('div');
    div.textContent = String(text);
    return div.innerHTML;
}

/**
 * Copy JSON to clipboard
 */
function copyJSON(button) {
    const jsonText = button.dataset.json;
    if (!jsonText) return;
    
    navigator.clipboard.writeText(jsonText).then(() => {
        const originalText = button.innerHTML;
        button.innerHTML = '✅ Copied!';
        button.classList.add('copied');
        setTimeout(() => {
            button.innerHTML = originalText;
            button.classList.remove('copied');
        }, 2000);
    }).catch(err => {
        console.error('Failed to copy:', err);
        alert('Failed to copy to clipboard');
    });
}

/**
 * Format message for dashboard activity feed
 */
function formatActivityMessage(message) {
    const typeIcon = getMessageTypeIcon(message.type || message.alert_type || message.alarm_type);
    const subType = formatMessageSubType(message);
    // Handle both timestamp (old) and tt/tt_string (new spec format)
    const timestamp = message.timestamp || (message.tt ? new Date(message.tt * 1000) : null) || new Date();
    const time = formatTimestamp(timestamp);
    const sourceHid = message.hid || message.source_device_hid || (message.source_device && message.source_device.hid) || 'Unknown Device';
    
    // Extract key info from payload (handle both msg and payload)
    let summary = '';
    const payload = message.msg || message.payload || {};
    if (payload && Object.keys(payload).length > 0) {
        if (payload.message || payload.text || payload.msg) {
            summary = payload.message || payload.text || payload.msg;
        } else if (payload.temperature !== undefined) {
            summary = `Temperature: ${payload.temperature}°C`;
        } else if (payload.status) {
            summary = `Status: ${payload.status}`;
        } else {
            summary = `${Object.keys(payload).length} data field${Object.keys(payload).length !== 1 ? 's' : ''}`;
        }
    }
    
    return {
        icon: typeIcon,
        type: subType,
        source: sourceHid,
        summary: summary,
        time: time,
        isAlarm: message.type === 'alarm'
    };
}

