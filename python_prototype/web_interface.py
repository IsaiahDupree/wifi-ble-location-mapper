#!/usr/bin/env python3
"""
Web Interface for WiFi & Bluetooth Location Detection System
Real-time visualization and control interface
"""

from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
import json
import threading
import time
from datetime import datetime

from main import CommunicationDetectionSystem

app = Flask(__name__)
app.config['SECRET_KEY'] = 'wifi_ble_detection_secret_key'
socketio = SocketIO(app, cors_allowed_origins="*")

# Global system instance
detection_system = None
system_thread = None

@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('dashboard.html')

@app.route('/api/status')
def get_status():
    """Get current system status"""
    if not detection_system:
        return jsonify({'status': 'stopped', 'message': 'System not running'})
    
    with detection_system.data_lock:
        latest_data = detection_system.latest_data.copy()
    
    status = {
        'status': 'running' if detection_system.running else 'stopped',
        'wifi_count': len(latest_data.get('wifi', [])),
        'bluetooth_count': len(latest_data.get('bluetooth', [])),
        'location': latest_data.get('location'),
        'signal_readings': len(detection_system.signal_mapper.signal_data),
        'timestamp': latest_data.get('timestamp')
    }
    
    return jsonify(status)

@app.route('/api/wifi')
def get_wifi_data():
    """Get current WiFi scan results"""
    if not detection_system:
        return jsonify([])
    
    with detection_system.data_lock:
        wifi_data = detection_system.latest_data.get('wifi', [])
    
    return jsonify(wifi_data)

@app.route('/api/bluetooth')
def get_bluetooth_data():
    """Get current Bluetooth scan results"""
    if not detection_system:
        return jsonify([])
    
    with detection_system.data_lock:
        bluetooth_data = detection_system.latest_data.get('bluetooth', [])
    
    return jsonify(bluetooth_data)

@app.route('/api/location')
def get_location_data():
    """Get current location data"""
    if not detection_system:
        return jsonify(None)
    
    location = detection_system.location_tracker.get_current_location()
    return jsonify(location)

@app.route('/api/heatmap/<signal_type>')
def get_heatmap_data(signal_type):
    """Get heatmap data for visualization"""
    if not detection_system:
        return jsonify({'data': []})
    
    identifier = request.args.get('identifier')
    heatmap_data = detection_system.signal_mapper.generate_heatmap_data(signal_type, identifier)
    
    return jsonify(heatmap_data)

@app.route('/api/analysis')
def get_analysis():
    """Get coverage analysis data"""
    if not detection_system:
        return jsonify({})
    
    wifi_analysis = detection_system.signal_mapper.analyze_coverage('wifi')
    bluetooth_analysis = detection_system.signal_mapper.analyze_coverage('bluetooth')
    
    return jsonify({
        'wifi': wifi_analysis,
        'bluetooth': bluetooth_analysis
    })

@socketio.on('start_system')
def handle_start_system():
    """Start the detection system"""
    global detection_system, system_thread
    
    if detection_system and detection_system.running:
        emit('system_message', {'type': 'warning', 'message': 'System already running'})
        return
    
    try:
        detection_system = CommunicationDetectionSystem()
        detection_system.start_time = time.time()
        
        # Override the callback to emit real-time updates
        original_callback = detection_system._on_data_update
        
        def web_callback(data_type, data):
            original_callback(data_type, data)
            socketio.emit('data_update', {
                'type': data_type,
                'data': data,
                'timestamp': datetime.now().isoformat()
            })
        
        detection_system._on_data_update = web_callback
        
        # Start system in separate thread
        system_thread = threading.Thread(target=detection_system.start_system)
        system_thread.daemon = True
        system_thread.start()
        
        emit('system_message', {'type': 'success', 'message': 'Detection system started'})
        
    except Exception as e:
        emit('system_message', {'type': 'error', 'message': f'Failed to start system: {str(e)}'})

@socketio.on('stop_system')
def handle_stop_system():
    """Stop the detection system"""
    global detection_system
    
    if not detection_system or not detection_system.running:
        emit('system_message', {'type': 'warning', 'message': 'System not running'})
        return
    
    try:
        detection_system.stop_system()
        emit('system_message', {'type': 'success', 'message': 'Detection system stopped'})
        
    except Exception as e:
        emit('system_message', {'type': 'error', 'message': f'Failed to stop system: {str(e)}'})

@socketio.on('export_data')
def handle_export_data():
    """Export current data"""
    if not detection_system:
        emit('system_message', {'type': 'warning', 'message': 'No system data to export'})
        return
    
    try:
        detection_system._export_all_data()
        emit('system_message', {'type': 'success', 'message': 'Data exported successfully'})
        
    except Exception as e:
        emit('system_message', {'type': 'error', 'message': f'Export failed: {str(e)}'})

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    print(f"Client connected: {request.sid}")
    emit('system_message', {'type': 'info', 'message': 'Connected to detection system'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    print(f"Client disconnected: {request.sid}")

if __name__ == '__main__':
    print("🌐 Starting Web Interface...")
    print("Open http://localhost:5000 in your browser")
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)
