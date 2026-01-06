"""
Maestra Quad-Core Sidecar Service

Runs on localhost:8826 and provides:
- Handshake endpoint for capability negotiation
- Library access bridge to local 8825 Library
- Learning profile injection
- Deep context aggregation from local brain services

This enables Quad-Core mode: Maestra UI + Local Sidecar + Local Backend + Local Brain
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import logging

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
SIDECAR_PORT = 8826
LIBRARY_PATH = Path(os.getenv(
    'LIBRARY_PATH',
    '/Users/justinharmon/Hammer Consulting Dropbox/Justin Harmon/8825-Team/shared/8825-library'
))

# Session store
_sessions = {}


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'maestra-sidecar',
        'version': '1.0.0',
        'timestamp': datetime.utcnow().isoformat(),
        'library_available': LIBRARY_PATH.exists(),
        'mode': 'quad-core'
    }), 200


@app.route('/handshake', methods=['POST'])
def handshake():
    """
    Quad-Core handshake endpoint
    
    Called by Maestra UI to establish Quad-Core connection
    Returns JWT, library ID, and available capabilities
    """
    try:
        data = request.get_json() or {}
        version = data.get('version', '1')
        user_agent = data.get('user_agent', 'unknown')
        
        logger.info(f'Handshake request: version={version}, user_agent={user_agent}')
        
        # Generate session token
        import secrets
        session_id = secrets.token_hex(16)
        
        # Determine available capabilities based on local services
        capabilities = [
            'library-access',      # Can read from local 8825 Library
            'learning-profiles',   # Can inject learning style preferences
            'deep-context',        # Can aggregate context from local brain
            'offline-mode',        # Can work offline with cached data
            'capability-routing',  # Can route to appropriate local services
        ]
        
        # Check if local brain is available
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('127.0.0.1', 5000))  # Jh-Brain port
            sock.close()
            if result == 0:
                capabilities.append('brain-routing')
        except:
            pass
        
        # Store session
        _sessions[session_id] = {
            'created_at': datetime.utcnow().isoformat(),
            'expires_at': (datetime.utcnow() + timedelta(hours=24)).isoformat(),
            'capabilities': capabilities,
            'user_agent': user_agent
        }
        
        response = {
            'success': True,
            'session_id': session_id,
            'jwt': f'sidecar.{session_id}',  # Pseudo-JWT for local use
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
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/library/<entry_id>', methods=['GET'])
def get_library_entry(entry_id: str):
    """
    Retrieve library entry from local 8825 Library
    
    Bridges Maestra UI requests to local library storage
    """
    try:
        # Sanitize entry_id
        if not entry_id.replace('-', '').replace('_', '').isalnum():
            return jsonify({'error': 'Invalid entry ID'}), 400
        
        entry_file = LIBRARY_PATH / f'{entry_id}.json'
        
        if not entry_file.exists():
            return jsonify({'error': f'Entry {entry_id} not found'}), 404
        
        with open(entry_file, 'r') as f:
            entry = json.load(f)
        
        logger.info(f'Retrieved library entry: {entry_id}')
        return jsonify({
            'success': True,
            'entry_id': entry_id,
            'entry': entry,
            'source': 'local-sidecar'
        }), 200
        
    except Exception as e:
        logger.error(f'Library retrieval error: {e}')
        return jsonify({'error': str(e)}), 500


@app.route('/capabilities', methods=['GET'])
def get_capabilities():
    """Get available Quad-Core capabilities"""
    session_id = request.args.get('session_id')
    
    if session_id and session_id in _sessions:
        session = _sessions[session_id]
        return jsonify({
            'session_id': session_id,
            'capabilities': session['capabilities'],
            'expires_at': session['expires_at']
        }), 200
    
    return jsonify({
        'capabilities': [
            'library-access',
            'learning-profiles',
            'deep-context',
            'offline-mode',
            'capability-routing',
        ]
    }), 200


@app.route('/context/aggregate', methods=['POST'])
def aggregate_context():
    """
    Aggregate deep context from local services
    
    Combines:
    - Library entries
    - Learning profiles
    - Conversation history
    - Local brain insights
    """
    try:
        data = request.get_json() or {}
        query = data.get('query', '')
        session_id = data.get('session_id')
        
        context = {
            'query': query,
            'sources': [],
            'aggregated_at': datetime.utcnow().isoformat(),
            'mode': 'quad-core'
        }
        
        # Add library context if query matches entry IDs
        import re
        entry_ids = re.findall(r'\b([a-f0-9]{16})\b', query.lower())
        if entry_ids and LIBRARY_PATH.exists():
            for entry_id in entry_ids:
                entry_file = LIBRARY_PATH / f'{entry_id}.json'
                if entry_file.exists():
                    try:
                        with open(entry_file, 'r') as f:
                            entry = json.load(f)
                        context['sources'].append({
                            'type': 'library',
                            'entry_id': entry_id,
                            'title': entry.get('title', 'Untitled'),
                            'source': entry.get('source', 'unknown')
                        })
                    except:
                        pass
        
        logger.info(f'Aggregated context for query: {query[:50]}...')
        return jsonify(context), 200
        
    except Exception as e:
        logger.error(f'Context aggregation error: {e}')
        return jsonify({'error': str(e)}), 500


@app.route('/status', methods=['GET'])
def status():
    """Get sidecar status"""
    return jsonify({
        'service': 'maestra-sidecar',
        'status': 'running',
        'port': SIDECAR_PORT,
        'mode': 'quad-core',
        'library_available': LIBRARY_PATH.exists(),
        'library_path': str(LIBRARY_PATH),
        'sessions_active': len(_sessions),
        'timestamp': datetime.utcnow().isoformat()
    }), 200


if __name__ == '__main__':
    logger.info(f'Starting Maestra Quad-Core Sidecar on port {SIDECAR_PORT}')
    logger.info(f'Library path: {LIBRARY_PATH}')
    logger.info(f'Library available: {LIBRARY_PATH.exists()}')
    app.run(host='127.0.0.1', port=SIDECAR_PORT, debug=False)
