from flask import Flask, request, jsonify, render_template, session, abort
from flask_sqlalchemy import SQLAlchemy
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

# Configure SQLite database URI (use /tmp/messages.db for Vercel deployment)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
    'DATABASE_URL',  # Use environment variable for production, fall back to /tmp for SQLite
    'sqlite:////tmp/messages.db'  # Default to /tmp/messages.db for local and Vercel
)
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

    def __repr__(self):
        return f"<Message {self.username}: {self.content}>"

# Create the database tables if they don't exist (NOTE: in production, use migrations instead)
with app.app_context():
    db.create_all()  # Only for development. In production, use Flask-Migrate for migrations.

# Global variable to keep track of active users
active_users = set()

# Endpoint to render the HTML page
@app.route('/')
def index():
    return render_template('chatbox.html')

# Endpoint to get messages from the database in JSON format
@app.route('/chat.json', methods=['GET'])
def get_messages():
    # Retrieve all messages from the database
    messages = Message.query.all()
    # Convert messages to a list of dictionaries
    return jsonify([{
        'id': message.id,
        'username': message.username,
        'content': message.content,
        'timestamp': message.timestamp
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
            # Create a new message instance
            new_message = Message(username=username, content=content, timestamp=timestamp)
            # Add to the database
            db.session.add(new_message)
            db.session.commit()
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
