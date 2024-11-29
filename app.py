from flask import Flask, request, jsonify, render_template, session, abort
from flask_pymongo import PyMongo
from dotenv import load_dotenv
from datetime import datetime
import uuid
import os

# Load environment variables
load_dotenv()

# Load secret key from environment variable (for better security)
SECRET_KEY = os.getenv('SECRET_KEY', 'your-default-secret-key')

# Initialize Flask app
app = Flask(__name__)

# Configure MongoDB URI (use environment variable for production, default to localhost for local dev)
app.config['MONGO_URI'] = os.getenv('MONGO_URI', 'mongodb://localhost:27017/chatbox')  # Replace with your MongoDB URI
app.config['SECRET_KEY'] = SECRET_KEY  # For session management

# Initialize PyMongo
mongo = PyMongo(app)

# Global variable to keep track of active users
active_users = set()

# Endpoint to render the HTML page
@app.route('/')
def index():
    return render_template('chatbox.html')

# Endpoint to get messages from MongoDB in JSON format
@app.route('/chat.json', methods=['GET'])
def get_messages():
    # Retrieve all messages from the MongoDB collection
    messages = mongo.db.messages.find()  # 'messages' is the collection name in MongoDB
    return jsonify([{
        'id': str(message['_id']),  # MongoDB uses ObjectId as the ID, so we convert it to string
        'username': message['username'],
        'content': message['content'],
        'timestamp': message['timestamp']
    } for message in messages])

# Endpoint to add a new message via POST
@app.route('/chat.json', methods=['POST'])
def post_message():
    try:
        data = request.get_json()
        username = data.get('username')
        content = data.get('content')
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if username and content:
            # Insert the new message into the MongoDB collection
            mongo.db.messages.insert_one({
                'username': username,
                'content': content,
                'timestamp': timestamp
            })
            return jsonify({'message': 'Message added successfully'}), 201
        else:
            return jsonify({'error': 'Invalid data'}), 400
    except Exception as e:
        # Log the error for debugging
        app.logger.error(f"Error posting message: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Endpoint to return the current online visitor count
@app.route('/visitor_count')
def visitor_count():
    # Return the current count of active users
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
    # Ensure app runs in debug mode only in development
    app.run(debug=True)
