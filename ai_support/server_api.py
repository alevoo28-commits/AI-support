@app.route('/api/report/latest', methods=['GET'])
def get_latest_report():
    if not os.path.exists(REPORTS_FILE):
        return jsonify({'error': 'No hay reportes'}), 404
    with open(REPORTS_FILE, 'r', encoding='utf-8') as f:
        reports = json.load(f)
    if not reports:
        return jsonify({'error': 'No hay reportes'}), 404
    return jsonify({'latest_report': reports[-1]}), 200
from flask import Flask, request, jsonify
from datetime import datetime
import os
import json

app = Flask(__name__)
REPORTS_FILE = 'connectivity_reports.json'
TRIGGER_FILE = 'trigger_test.json'

# Crea el archivo si no existe
if not os.path.exists(REPORTS_FILE):
    with open(REPORTS_FILE, 'w', encoding='utf-8') as f:
        json.dump([], f)

@app.route('/api/report', methods=['POST'])
def report():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data received'}), 400
    # Agrega timestamp si no viene
    if 'timestamp' not in data:
        data['timestamp'] = datetime.now().isoformat()
    # Guarda el reporte
    with open(REPORTS_FILE, 'r+', encoding='utf-8') as f:
        reports = json.load(f)
        reports.append(data)
        f.seek(0)
        json.dump(reports, f, ensure_ascii=False, indent=2)
    return jsonify({'status': 'ok', 'received': data}), 200

@app.route('/api/trigger-test', methods=['POST'])
def trigger_test():
    data = request.get_json()
    if not data or 'client_id' not in data:
        return jsonify({'error': 'client_id requerido'}), 400
    # Guarda el trigger para el cliente
    with open(TRIGGER_FILE, 'w', encoding='utf-8') as f:
        json.dump({'client_id': data['client_id'], 'timestamp': datetime.now().isoformat()}, f)
    return jsonify({'status': 'triggered', 'client_id': data['client_id']}), 200

@app.route('/api/trigger-test', methods=['GET'])
def get_trigger():
    # El cliente consulta si hay trigger pendiente
    if not os.path.exists(TRIGGER_FILE):
        return jsonify({'trigger': False}), 200
    with open(TRIGGER_FILE, 'r', encoding='utf-8') as f:
        trigger = json.load(f)
    return jsonify({'trigger': True, 'client_id': trigger.get('client_id'), 'timestamp': trigger.get('timestamp')}), 200

@app.route('/api/trigger-test/clear', methods=['POST'])
def clear_trigger():
    # El cliente borra el trigger después de ejecutarlo
    if os.path.exists(TRIGGER_FILE):
        os.remove(TRIGGER_FILE)
    return jsonify({'status': 'cleared'}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
