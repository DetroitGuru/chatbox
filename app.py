from flask import Flask, request, jsonify, render_template, session, abort
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
from datetime import datetime
import uuid
import os

# Load environment variables
load_dotenv()

# Load secret key from environment variable
SECRET_KEY = os.getenv('SECRET_KEY', 'your-default-secret-key')

# Initialize Flask app
app = Flask(__name__)

# Configure PostgreSQL database URI (use environment variable)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'postgresql://username:password@localhost/your_database_name')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # Disable modification tracking
app.config['SECRET_KEY'] = SECRET_KEY  # For session management

# Initialize SQLAlchemy
db = SQLAlchemy(app)

# Define Message model
class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.String(20), nullable=False)
    user_id = db.Column(db.String(36), nullable=False)

    def __repr__(self):
        return f"<Message {self.username}: {self.content}>"

# Create the database tables if they don't exist
with app.app_context():
    db.create_all()  # For PostgreSQL, creates the tables in the specified database

# Global variable to keep track of active users
active_users = set()

# Endpoint to render the HTML page
@app.route('/')
def index():
    return render_template('chatbox.html')

# Endpoint to get messages from the database in JSON format
@app.route('/messages', methods=['GET'])
def get_messages():
    messages = Message.query.all()
    return jsonify([{
        'id': message.id,
        'username': message.username,
        'content': message.content,
        'timestamp': message.timestamp
    } for message in messages])

# Endpoint to add a new message via POST
@app.route('/messages', methods=['POST'])
def post_message():
    try:
        data = request.get_json()
        username = data.get('username')
        content = data.get('content')
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if username and content:
            new_message = Message(username=username, content=content, timestamp=timestamp, user_id=session.get('user_id'))
            db.session.add(new_message)
            db.session.commit()
            return jsonify({'message': 'Message added successfully'}), 201
        else:
            return jsonify({'error': 'Invalid data'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500
        
#Endpoint to edit a specific user messages
@app.route('/messages/<int:id>', methods=['PUT'])
def edit_message(id):
    try:
        data = request.get_json()
        content = data.get('content')
        message = Message.query.get(id)

        if message and message.user_id == session.get('user_id'):  # Ensure the user owns the message
            message.content = content
            db.session.commit()
            return jsonify({"message": "Message updated successfully"}), 200
        else:
            return jsonify({"error": "Message not found or you don't have permission to edit this message"}), 403
    except Exception as e:
        return jsonify({"error": str(e)}), 500
        
#Endpoint to delete a specific user messages
@app.route('/messages/<int:id>', methods=['DELETE'])
def delete_message(id):
    try:
        message = Message.query.get(id)

        if message and message.user_id == session.get('user_id'):  # Ensure the user owns the message
            db.session.delete(message)
            db.session.commit()
            return jsonify({"message": "Message deleted successfully"}), 200
        else:
            return jsonify({"error": "Message not found or you don't have permission to delete this message"}), 403
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Endpoint to return the current online visitor count
@app.route('/visitor_count')
def visitor_count():
    return jsonify({"visitor_count": len(active_users)})

# Handle user joining (for example, by using a session ID)
@app.before_request
def track_user():
    user_id = str(uuid.uuid4())  # Generate a unique session ID for the user
    if 'user_id' not in session:
        session['user_id'] = user_id
        active_users.add(user_id)

# Handle user leaving (cleanup when they disconnect)
@app.teardown_request
def cleanup_user(exception=None):
    user_id = session.get('user_id')
    if user_id and user_id in active_users:
        active_users.remove(user_id)

if __name__ == '__main__':
    app.run(debug=True)
