import os
from flask import Flask, request, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_caching import Cache
import requests
import jwt
import logging
from functools import wraps
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['BACKEND_URL'] = os.getenv('BACKEND_URL')
app.config['CACHE_TYPE'] = 'simple'
app.config['CACHE_DEFAULT_TIMEOUT'] = 300

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Setup rate limiting
limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

# Setup caching
cache = Cache(app)

# JWT Authentication
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'message': 'Token is missing!'}), 401
        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
        except:
            return jsonify({'message': 'Token is invalid!'}), 401
        return f(*args, **kwargs)
    return decorated

# Middleware function to log requests
@app.before_request
def log_request_info():
    logger.info('Headers: %s', request.headers)
    logger.info('Body: %s', request.get_data())

# Error handler
@app.errorhandler(Exception)
def handle_error(error):
    logger.error(f"An error occurred: {str(error)}", exc_info=True)
    message = str(error)
    status_code = 500
    if hasattr(error, 'code'):
        status_code = error.code
    return jsonify({"error": message}), status_code

# Health check endpoint
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy"}), 200

# Main API route
@app.route('/api/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE'])
@token_required
@limiter.limit("10 per minute")
@cache.cached(timeout=60, query_string=True)
def middleware(path):
    try:
        # Forward the request to the backend
        if request.method == 'GET':
            response = requests.get(f"{app.config['BACKEND_URL']}/{path}", params=request.args, headers=request.headers)
        elif request.method == 'POST':
            response = requests.post(f"{app.config['BACKEND_URL']}/{path}", json=request.json, headers=request.headers)
        elif request.method == 'PUT':
            response = requests.put(f"{app.config['BACKEND_URL']}/{path}", json=request.json, headers=request.headers)
        elif request.method == 'DELETE':
            response = requests.delete(f"{app.config['BACKEND_URL']}/{path}", params=request.args, headers=request.headers)
        
        # Process the response
        data = response.json()
        
        # Log the response
        logger.info(f"Response from backend: {data}")
        
        # Return the processed response to the frontend
        return jsonify(data), response.status_code
    
    except requests.RequestException as e:
        logger.error(f"Error communicating with backend: {str(e)}")
        return jsonify({"error": "Error communicating with backend"}), 503

# User registration endpoint
@app.route('/register', methods=['POST'])
def register():
    # This would typically involve creating a user in your database
    # For this example, we'll just return a success message
    return jsonify({"message": "User registered successfully"}), 201

# User login endpoint
@app.route('/login', methods=['POST'])
def login():
    # This would typically involve checking credentials against your database
    # For this example, we'll just create a token
    token = jwt.encode({'user_id': request.json.get('username')}, app.config['SECRET_KEY'], algorithm="HS256")
    return jsonify({'token': token})

if __name__ == '__main__':
    app.run(debug=True)