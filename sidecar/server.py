"""
Maestra Quad-Core Sidecar Service
Runs on localhost:8826 with proper CORS for browser access
"""

from flask import Flask, jsonify, request
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import logging
import secrets

# Configuration FIRST
SIDECAR_PORT = 8826
LIBRARY_PATH = Path(os.getenv(
    'LIBRARY_PATH',
    '/Users/justinharmon/Hammer Consulting Dropbox/Justin Harmon/8825-Team/shared/8825-library'
))

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Session store
_sessions = {}

@app.after_request
def add_cors_headers(response):
    """Add CORS headers to EVERY response"""
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With'
    response.headers['Access-Control-Max-Age'] = '3600'
    return response

@app.route('/health', methods=['GET', 'OPTIONS'])
def health():
    if request.method == 'OPTIONS':
        return '', 204
    return jsonify({
        'status': 'healthy',
        'service': 'maestra-sidecar',
        'version': '1.0.0',
        'timestamp': datetime.utcnow().isoformat(),
        'library_available': LIBRARY_PATH.exists(),
        'mode': 'quad-core'
    }), 200

@app.route('/handshake', methods=['POST', 'OPTIONS'])
def handshake():
    if request.method == 'OPTIONS':
        return '', 204
    try:
        data = request.get_json() or {}
        version = data.get('version', '1')
        user_agent = data.get('user_agent', 'unknown')
        
        logger.info(f'Handshake request: version={version}, user_agent={user_agent}')
        
        session_id = secrets.token_hex(16)
        
        capabilities = [
            'library-access',
            'learning-profiles',
            'deep-context',
            'offline-mode',
            'capability-routing',
        ]
        
        # Check if local brain is available
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('127.0.0.1', 5000))
            sock.close()
            if result == 0:
                capabilities.append('brain-routing')
        except:
            pass
        
        _sessions[session_id] = {
            'created_at': datetime.utcnow().isoformat(),
            'expires_at': (datetime.utcnow() + timedelta(hours=24)).isoformat(),
            'capabilities': capabilities,
            'user_agent': user_agent
        }
        
        response = {
            'success': True,
            'session_id': session_id,
            'jwt': f'sidecar.{session_id}',
            'library_id': 'local-8825-library',
            'capabilities': capabilities,
            'mode': 'quad-core',
            'expires_at': (datetime.utcnow() + timedelta(hours=24)).isoformat(),
            'library_path': str(LIBRARY_PATH) if LIBRARY_PATH.exists() else None,
        }
        
        logger.info(f'Handshake successful: {session_id}')
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f'Handshake error: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/library/<entry_id>', methods=['GET', 'OPTIONS'])
def get_library_entry(entry_id):
    if request.method == 'OPTIONS':
        return '', 204
    try:
        if not entry_id.replace('-', '').replace('_', '').isalnum():
            return jsonify({'error': 'Invalid entry ID'}), 400
        
        entry_file = LIBRARY_PATH / f'{entry_id}.json'
        
        if not entry_file.exists():
            return jsonify({'error': f'Entry {entry_id} not found'}), 404
        
        with open(entry_file, 'r') as f:
            entry = json.load(f)
        
        return jsonify({
            'success': True,
            'entry_id': entry_id,
            'entry': entry,
            'source': 'local-sidecar'
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/status', methods=['GET', 'OPTIONS'])
def status():
    if request.method == 'OPTIONS':
        return '', 204
    return jsonify({
        'service': 'maestra-sidecar',
        'status': 'running',
        'port': SIDECAR_PORT,
        'mode': 'quad-core',
        'library_available': LIBRARY_PATH.exists(),
        'sessions_active': len(_sessions),
        'timestamp': datetime.utcnow().isoformat()
    }), 200

if __name__ == '__main__':
    logger.info(f'Starting Maestra Quad-Core Sidecar on port {SIDECAR_PORT}')
    logger.info(f'Library path: {LIBRARY_PATH}')
    app.run(host='127.0.0.1', port=SIDECAR_PORT, debug=False)
