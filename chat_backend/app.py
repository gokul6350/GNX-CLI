import os
import datetime
import json
from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy

# Configure paths
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "gnx_history.db")
IMG_DIR = os.path.join(BASE_DIR, "static", "images")

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_PATH}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Ensure image directory exists
os.makedirs(IMG_DIR, exist_ok=True)

# --- Models ---
class Session(db.Model):
    id = db.Column(db.String(50), primary_key=True)
    name = db.Column(db.String(100))
    start_time = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    logs = db.relationship('LogEntry', backref='session', lazy=True, cascade="all, delete-orphan")

class LogEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(50), db.ForeignKey('session.id'), nullable=False)
    type = db.Column(db.String(20))  # user, ai, tool_call, tool_result, system, image
    content = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    is_context = db.Column(db.Boolean, default=False) # True if this is part of the LLM context
    metadata_json = db.Column(db.Text, nullable=True) # Extra data like token count, tool name

# --- Routes ---

@app.route('/')
def index():
    sessions = Session.query.order_by(Session.start_time.desc()).all()
    return render_template('index.html', sessions=sessions)

@app.route('/session/<session_id>')
def view_session(session_id):
    session = Session.query.get_or_404(session_id)
    logs = LogEntry.query.filter_by(session_id=session_id).order_by(LogEntry.timestamp).all()
    return render_template('session.html', session=session, logs=logs)

# --- API ---

@app.route('/api/session', methods=['POST'])
def create_session():
    data = request.json
    session_id = data.get('id')
    name = data.get('name', f"Session {session_id}")
    
    if not session_id:
        return jsonify({"error": "Session ID required"}), 400
        
    if db.session.get(Session, session_id):
        return jsonify({"message": "Session already exists"}), 200
        
    new_session = Session(id=session_id, name=name)
    db.session.add(new_session)
    db.session.commit()
    return jsonify({"message": "Session created", "id": session_id}), 201

@app.route('/api/log', methods=['POST'])
def add_log():
    data = request.json
    session_id = data.get('session_id')
    
    if not session_id:
        return jsonify({"error": "Session ID required"}), 400
        
    # Ensure session exists (in case of race condition or restart)
    if not db.session.get(Session, session_id):
        new_session = Session(id=session_id, name=f"Session {session_id}")
        db.session.add(new_session)
        db.session.commit()

    metadata = data.get('metadata', {})
    if isinstance(metadata, dict):
        metadata = json.dumps(metadata)

    log = LogEntry(
        session_id=session_id,
        type=data.get('type', 'system'),
        content=data.get('content', ''),
        is_context=data.get('is_context', False),
        metadata_json=metadata
    )
    db.session.add(log)
    db.session.commit()
    return jsonify({"message": "Log added", "id": log.id}), 201

@app.route('/api/image', methods=['POST'])
def upload_image():
    if 'image' not in request.files:
        return jsonify({"error": "No image part"}), 400
        
    file = request.files['image']
    session_id = request.form.get('session_id')
    
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
        
    if file and session_id:
        filename = f"{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}"
        filepath = os.path.join(IMG_DIR, filename)
        file.save(filepath)
        
        # Add log entry for image
        log = LogEntry(
            session_id=session_id,
            type='image',
            content=f"/static/images/{filename}",
            is_context=False # Images usually handled separately or via multimodal context
        )
        db.session.add(log)
        db.session.commit()
        
        return jsonify({"message": "Image uploaded", "path": log.content}), 201
        
    return jsonify({"error": "Missing data"}), 400

def init_db():
    with app.app_context():
        db.create_all()

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000, use_reloader=False)
