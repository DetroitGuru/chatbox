from flask import Flask, request, jsonify, render_template, session
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
from datetime import datetime
import uuid
import os
import re

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

# Define Message model with indexing for performance optimization
class Message(db.Model):
    __tablename__ = 'messages'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.String(20), nullable=False)
    user_id = db.Column(db.String(36), nullable=False, index=True)  # Indexed for faster queries
    __table_args__ = (db.Index('ix_messages_timestamp', 'timestamp'),)  # Index on timestamp for faster retrieval

    def __repr__(self):
        return f"<Message {self.username}: {self.content}>"

# Create the database tables if they don't exist
with app.app_context():
    db.create_all()

# Global variable to keep track of active users (session-based)
active_users = set()

# Load profane words from the file
def load_bad_words():
    with open('bad_words.txt', 'r') as file:
        # Return a set of bad words (to optimize search performance)
        return set(line.strip().lower() for line in file.readlines())

BAD_WORDS = load_bad_words()  # Load the bad words when the app starts

# Function to replace profanity in the text with asterisks
def replace_profanity(text):
    for bad_word in BAD_WORDS:
        # Replace each bad word with the equivalent number of asterisks, preserving case
        text = re.sub(r'\b' + re.escape(bad_word) + r'\b', lambda m: '*' * len(m.group(0)), text)
    return text
    
# Endpoint to render the HTML page
@app.route('/')
def index():
    return render_template('chatbox.html')

# Endpoint to get messages from the database in JSON format
@app.route('/messages', methods=['GET'])
def get_messages():
    try:
        messages = Message.query.order_by(Message.timestamp.asc()).all()
        return jsonify([{
            'id': message.id,
            'username': message.username,
            'content': message.content,
            'timestamp': message.timestamp
        } for message in messages])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Function to limit the message to 100 characters
def limit_message_length(content, max_length=100):
    if len(content) > max_length:
        content = content[:max_length]  # Truncate to the first 100 characters
    return content

# Endpoint to add a new message via POST
@app.route('/messages', methods=['POST'])
def post_message():
    try:
        data = request.get_json()
        username = data.get('username')
        content = data.get('content')
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        user_id = session.get('user_id')

        if not username or not content:
            return jsonify({'error': 'Invalid data, username and content required'}), 400

        if not user_id:
            return jsonify({'error': 'User session expired or not found'}), 400

        # Limit the message to 100 characters
        limited_content = limit_message_length(content)
        
        # Check if content was truncated and return feedback
        if len(content) > 100:
            return jsonify({
                'message': 'Your message was too long and has been truncated to 100 characters.',
                'content': limited_content
            }), 200

        # Replace profanity in the content with asterisks
        sanitized_content = replace_profanity(limited_content)

        new_message = Message(username=username, content=sanitized_content, timestamp=timestamp, user_id=user_id)
        db.session.add(new_message)
        db.session.commit()
        return jsonify({'message': 'Message added successfully'}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Endpoint for retrieving a specific user's message
@app.route('/messages/<int:id>', methods=['GET'])
def get_message(id):
    message = Message.query.get(id)
    if message:
        return jsonify({
            'id': message.id,
            'username': message.username,
            'content': message.content,
            'timestamp': message.timestamp
        })
    else:
        return jsonify({'error': 'Message not found'}), 404

# Endpoint to edit a specific user's message
@app.route('/messages/<int:id>', methods=['PUT'])
def edit_message(id):
    try:
        data = request.get_json()
        content = data.get('content')
        message = Message.query.get(id)

        if message and message.user_id == session.get('user_id'):  # Ensure the user owns the message
            # Limit the message to 100 characters
            limited_content = limit_message_length(content)
            
            # Check if content was truncated and return feedback
        if len(content) > 100:
            return jsonify({
                'message': 'Your message was too long and has been truncated to 100 characters.',
                'content': limited_content
            }), 200

            # Replace profanity in the new content with asterisks
            sanitized_content = replace_profanity(limited_content)
            message.content = sanitized_content
            db.session.commit()
            return jsonify({"message": "Message updated successfully"}), 200
        else:
            return jsonify({"error": "Message not found or you don't have permission to edit this message"}), 403
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Endpoint to delete a specific user's message
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
    if 'user_id' not in session:
        session['user_id'] = str(uuid.uuid4())  # Generate a unique session ID for the user
    active_users.add(session['user_id'])

# Handle user leaving (cleanup when they disconnect)
@app.teardown_request
def cleanup_user(exception=None):
    user_id = session.get('user_id')
    if user_id and user_id in active_users:
        active_users.remove(user_id)

if __name__ == '__main__':
    app.run(debug=True)
