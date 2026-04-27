"""
LAHSO Flask Web Application
Integrates the existing LAHSO Python code with the new HTML/JavaScript UI
"""
import os
import sys

import json
import asyncio
from pathlib import Path
from threading import Thread
import time
import uuid
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_ROOT = PROJECT_ROOT / "src"

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

# Load environment variables from .env file
load_dotenv()

from flask import Flask, render_template_string, request, jsonify, session
from flask_socketio import SocketIO, emit, join_room, leave_room
import pandas as pd

# Import existing LAHSO modules
from lahso.config import Config
from lahso.model_input import ModelInput
from lahso.model_train import model_train
from lahso.model_implementation import model_implementation
from lahso.kbest import kbest
from lahso.service_to_path import service_to_path
from lahso.bar_chart_plot import comparison
from lahso.paths import (
    DEFAULT_GUROBI_LICENSE_FILE,
    project_relative,
    Q_TABLES_DIR,
    RAW_DISRUPTIONS_DIR,
    TRAINING_METRICS_DIR,
    WEB_TEMPLATES_DIR,
    ensure_directories,
)

if "GRB_LICENSE_FILE" not in os.environ and DEFAULT_GUROBI_LICENSE_FILE.exists():
    os.environ["GRB_LICENSE_FILE"] = str(DEFAULT_GUROBI_LICENSE_FILE)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv("LAHSO_SECRET_KEY", "lahso_dev_secret_key")
socketio = SocketIO(app, cors_allowed_origins="*")

# Global state management
active_sessions = {}
training_processes = {}
simulation_processes = {}

class LAHSOSession:
    def __init__(self, session_id):
        self.session_id = session_id
        self.config = Config()
        self.model_input = None
        self.training_generator = None
        self.simulation_generator = None
        self.training_active = False
        self.simulation_active = False
        self.training_paused = False
        self.current_episode = 0
        self.total_episodes = 0
        
    def to_dict(self):
        return {
            'session_id': self.session_id,
            'training_active': self.training_active,
            'simulation_active': self.simulation_active,
            'training_paused': self.training_paused,
            'current_episode': self.current_episode,
            'total_episodes': self.total_episodes
        }

def get_session():
    """Get or create session for current user"""
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    
    session_id = session['session_id']
    if session_id not in active_sessions:
        active_sessions[session_id] = LAHSOSession(session_id)
    
    return active_sessions[session_id]

@app.route('/')
def index():
    """Serve the main HTML page"""
    # Read the HTML content
    html_file = WEB_TEMPLATES_DIR / "index.html"
    if html_file.exists():
        with open(html_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
        return render_template_string(html_content)
    else:
        return "HTML template not found. Please create templates/index.html", 404

@app.route('/api/config/default', methods=['GET'])
def get_default_config():
    """Get default configuration values"""
    try:
        config = Config()
        return jsonify({
            'success': True,
            'config': {
                'storage_cost': config.storage_cost if hasattr(config, 'storage_cost') else 1,
                'delay_penalty': config.delay_penalty if hasattr(config, 'delay_penalty') else 1,
                'undelivered_penalty': config.undelivered_penalty if hasattr(config, 'undelivered_penalty') else 100,
                'learning_rate': 0.5,
                'exploratory_rate': 0.95,
                'num_simulations': 50000,
                'simulation_duration': 42,
                'impl_num_simulations': 20,
                'impl_duration': 35
            },
            'default_files': {
                'network': project_relative(config.network_path),
                'network_barge': project_relative(config.network_barge_path),
                'network_train': project_relative(config.network_train_path),
                'network_truck': project_relative(config.network_truck_path),
                'fixed_schedule': project_relative(config.fixed_service_schedule_path),
                'truck_schedule': project_relative(config.truck_schedule_path),
                'demand': project_relative(config.demand_default_path),
                'mode_costs': project_relative(config.mode_costs_path),
                'service_disruptions': project_relative(config.s_disruption_path),
                'demand_disruptions': project_relative(config.d_disruption_path),
                'q_table': project_relative(config.q_table_path)
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/dataset/validate', methods=['POST'])
def validate_dataset():
    """Validate dataset input and prepare configuration"""
    try:
        data = request.json
        lahso_session = get_session()
        
        # Create config with dataset parameters
        config = Config(
            print_event_enabled=False,
            demand_type="kbest" if data.get('compute_kbest', True) else "default",
            storage_cost=int(data.get('storage_cost', 1)),
            delay_penalty=int(data.get('delay_penalty', 1)),
            undelivered_penalty=int(data.get('undelivered_penalty', 100)),
        )
        
        # Run preprocessing
        service_to_path(config)
        if data.get('compute_kbest', True):
            kbest(config)
        
        lahso_session.config = config
        
        return jsonify({
            'success': True,
            'message': 'Dataset validated successfully',
            'kbest_generated': data.get('compute_kbest', True)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/training/configure', methods=['POST'])
def configure_training():
    """Configure training parameters"""
    try:
        data = request.json
        lahso_session = get_session()
        
        # Update training configuration
        default_config = Config()
        lahso_session.config.s_disruption_path = default_config.s_disruption_path
        lahso_session.config.d_disruption_path = default_config.d_disruption_path
        lahso_session.config.alpha = float(data.get('learning_rate', 0.5))
        lahso_session.config.epsilon = float(data.get('exploratory_rate', 0.95))
        lahso_session.config.number_of_simulation = int(data.get('num_simulations', 50000))
        lahso_session.config.simulation_duration = int(data.get('simulation_duration', 42)) * 1440  # Convert to minutes
        lahso_session.config.extract_q_table = 1
        lahso_session.config.start_from_0 = not data.get('continue_training', False)
        lahso_session.config.q_table_path = Q_TABLES_DIR / "default_q_table_output.pkl"
        lahso_session.config.tc_path = TRAINING_METRICS_DIR / "default_total_cost_output.pkl"
        lahso_session.config.tr_path = TRAINING_METRICS_DIR / "default_total_reward_output.pkl"
        
        lahso_session.total_episodes = lahso_session.config.number_of_simulation
        lahso_session.model_input = ModelInput(lahso_session.config)
        
        return jsonify({
            'success': True,
            'message': 'Training configuration updated',
            'total_episodes': lahso_session.total_episodes
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/training/start', methods=['POST'])
def start_training():
    """Start training process"""
    try:
        lahso_session = get_session()
        
        if lahso_session.training_active:
            return jsonify({'success': False, 'error': 'Training already active'})
        
        lahso_session.training_active = True
        lahso_session.training_paused = False
        lahso_session.current_episode = 0
        
        # Start training in background thread
        training_thread = Thread(
            target=run_training_background,
            args=(lahso_session.session_id,)
        )
        training_thread.daemon = True
        training_thread.start()
        
        return jsonify({
            'success': True,
            'message': 'Training started',
            'session_id': lahso_session.session_id
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/training/pause', methods=['POST'])
def pause_training():
    """Pause training process"""
    try:
        lahso_session = get_session()
        lahso_session.training_paused = True
        
        return jsonify({
            'success': True,
            'message': 'Training paused'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/training/resume', methods=['POST'])
def resume_training():
    """Resume training process"""
    try:
        lahso_session = get_session()
        
        if not lahso_session.training_active:
            return jsonify({'success': False, 'error': 'No training session active'})
        
        lahso_session.training_paused = False
        
        return jsonify({
            'success': True,
            'message': 'Training resumed'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/training/stop', methods=['POST'])
def stop_training():
    """Stop training process"""
    try:
        lahso_session = get_session()
        lahso_session.training_active = False
        lahso_session.training_paused = False
        
        return jsonify({
            'success': True,
            'message': 'Training stopped'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/implementation/configure', methods=['POST'])
def configure_implementation():
    """Configure implementation parameters"""
    try:
        data = request.json
        lahso_session = get_session()
        
        # Create implementation config
        config = Config(
            s_disruption_path=RAW_DISRUPTIONS_DIR / "No_Service_Disruption_Profile.csv",
            d_disruption_path=RAW_DISRUPTIONS_DIR / "No_Request_Disruption_Profile.csv",
            number_of_simulation=int(data.get('num_simulations', 20)),
            simulation_duration=int(data.get('simulation_duration', 35)) * 1440,  # Convert to minutes
            start_from_0=True,
            q_table_path=Q_TABLES_DIR / "default_q_table_output.pkl",
            policy_name=data.get('policy', 'gp'),
            extract_shipment_output=True,
        )
        
        # Copy dataset config from training
        if hasattr(lahso_session.config, 'network_path'):
            config.network_path = lahso_session.config.network_path
            config.network_barge_path = lahso_session.config.network_barge_path
            config.network_train_path = lahso_session.config.network_train_path
            config.network_truck_path = lahso_session.config.network_truck_path
            config.fixed_service_schedule_path = lahso_session.config.fixed_service_schedule_path
            config.truck_schedule_path = lahso_session.config.truck_schedule_path
            config.demand_default_path = lahso_session.config.demand_default_path
            config.demand_kbest_path = lahso_session.config.demand_kbest_path
            config.mode_costs_path = lahso_session.config.mode_costs_path
            config.storage_cost = lahso_session.config.storage_cost
            config.delay_penalty = lahso_session.config.delay_penalty
            config.undelivered_penalty = lahso_session.config.undelivered_penalty
            config.demand_type = lahso_session.config.demand_type
        
        lahso_session.config = config
        lahso_session.model_input = ModelInput(config)
        
        return jsonify({
            'success': True,
            'message': 'Implementation configuration updated'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/implementation/execute', methods=['POST'])
def execute_implementation():
    """Execute implementation simulation"""
    try:
        lahso_session = get_session()
        
        if lahso_session.simulation_active:
            return jsonify({'success': False, 'error': 'Simulation already active'})
        
        lahso_session.simulation_active = True
        
        # Start simulation in background thread
        simulation_thread = Thread(
            target=run_simulation_background,
            args=(lahso_session.session_id,)
        )
        simulation_thread.daemon = True
        simulation_thread.start()
        
        return jsonify({
            'success': True,
            'message': 'Simulation started',
            'session_id': lahso_session.session_id
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/comparison/compare', methods=['POST'])
def compare_results():
    """Compare two result files"""
    try:
        data = request.json
        file1_path = data.get('file1_path')
        file2_path = data.get('file2_path')
        label1 = data.get('label1', 'Policy 1')
        label2 = data.get('label2', 'Policy 2')
        
        if not file1_path or not file2_path:
            return jsonify({'success': False, 'error': 'Both files required'})
        
        # Use the existing comparison function
        comparison_data = comparison(file1_path, file2_path, label1, label2)
        
        return jsonify({
            'success': True,
            'comparison_data': comparison_data.to_dict('records'),
            'message': 'Comparison completed successfully'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

def run_training_background(session_id):
    """Run training in background thread"""
    try:
        lahso_session = active_sessions[session_id]
        
        # Create training generator
        training_gen = model_train(lahso_session.config, lahso_session.model_input)
        
        for result in training_gen:
            if not lahso_session.training_active:
                break
                
            while lahso_session.training_paused:
                time.sleep(1)
                if not lahso_session.training_active:
                    break
            
            if result is not None:
                # Extract episode info
                if 'Episode' in result.columns:
                    lahso_session.current_episode = result['Episode'].max()
                
                # Emit progress via WebSocket
                socketio.emit('training_progress', {
                    'session_id': session_id,
                    'episode': lahso_session.current_episode,
                    'total_episodes': lahso_session.total_episodes,
                    'data': result.to_dict('records') if len(result) < 1000 else result.tail(100).to_dict('records')
                }, room=session_id)
                
            time.sleep(0.1)  # Prevent overwhelming the client
        
        lahso_session.training_active = False
        socketio.emit('training_complete', {
            'session_id': session_id,
            'message': 'Training completed successfully'
        }, room=session_id)
        
    except Exception as e:
        lahso_session.training_active = False
        socketio.emit('training_error', {
            'session_id': session_id,
            'error': str(e)
        }, room=session_id)

def run_simulation_background(session_id):
    """Run simulation in background thread"""
    try:
        lahso_session = active_sessions[session_id]
        
        # Create simulation generator
        simulation_gen = model_implementation(lahso_session.config, lahso_session.model_input)
        
        for result in simulation_gen:
            if not lahso_session.simulation_active:
                break
            
            if result is not None:
                # Emit progress via WebSocket
                socketio.emit('simulation_progress', {
                    'session_id': session_id,
                    'data': result.to_dict('records')
                }, room=session_id)
                
            time.sleep(0.5)  # Slower updates for simulation
        
        lahso_session.simulation_active = False
        socketio.emit('simulation_complete', {
            'session_id': session_id,
            'message': 'Simulation completed successfully'
        }, room=session_id)
        
    except Exception as e:
        lahso_session.simulation_active = False
        socketio.emit('simulation_error', {
            'session_id': session_id,
            'error': str(e)
        }, room=session_id)

# WebSocket events
@socketio.on('connect')
def handle_connect():
    lahso_session = get_session()
    join_room(lahso_session.session_id)
    emit('connected', {'session_id': lahso_session.session_id})

@socketio.on('disconnect')
def handle_disconnect():
    lahso_session = get_session()
    leave_room(lahso_session.session_id)

@socketio.on('join_session')
def handle_join_session(data):
    session_id = data.get('session_id')
    if session_id:
        join_room(session_id)

if __name__ == '__main__':
    # Ensure required directories exist
    ensure_directories(
        WEB_TEMPLATES_DIR,
        Q_TABLES_DIR,
        TRAINING_METRICS_DIR,
    )
    
    print("🚀 LAHSO Web Application starting...")
    print("📡 Access the application at: http://localhost:5000")
    
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
