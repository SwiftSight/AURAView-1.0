import os
from flask import Flask, request, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_caching import Cache
from flask_cors import CORS
import requests
import jwt
import logging
from functools import wraps
from dotenv import load_dotenv
from marshmallow import Schema, fields, ValidationError

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['BACKEND_URL'] = os.getenv('BACKEND_URL')
app.config['CACHE_TYPE'] = 'simple'
app.config['CACHE_DEFAULT_TIMEOUT'] = 300
app.config['JWT_EXPIRATION_DELTA'] = 7200  # Token expiration time in seconds (2 hours)

# Setup CORS
CORS(app, resources={r"/api/*": {"origins": "*"}})

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

# Input validation schemas
class LoginSchema(Schema):
    username = fields.Str(required=True)
    password = fields.Str(required=True)

class RegisterSchema(Schema):
    username = fields.Str(required=True)
    password = fields.Str(required=True)
    email = fields.Email(required=True)

# JWT Authentication
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'message': 'Token is missing!'}), 401
        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            if 'exp' in data and data['exp'] < int(time.time()):
                return jsonify({'message': 'Token has expired!'}), 401
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token has expired!'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Token is invalid!'}), 401
        return f(*args, **kwargs)
    return decorated

# Middleware function to log requests
@app.before_request
def log_request_info():
    logger.info('Headers: %s', request.headers)
    logger.info('Body: %s', request.get_data())

# Middleware to add security headers
@app.after_request
def add_security_headers(response):
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    return response

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
        headers = {key: value for (key, value) in request.headers if key != 'Host'}
        url = f"{app.config['BACKEND_URL']}/{path}"

        if request.method == 'GET':
            response = requests.get(url, params=request.args, headers=headers)
        elif request.method == 'POST':
            response = requests.post(url, json=request.json, headers=headers)
        elif request.method == 'PUT':
            response = requests.put(url, json=request.json, headers=headers)
        elif request.method == 'DELETE':
            response = requests.delete(url, params=request.args, headers=headers)
        
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
@limiter.limit("5 per hour")
def register():
    try:
        data = RegisterSchema().load(request.json)
    except ValidationError as err:
        return jsonify(err.messages), 400

    # This would typically involve creating a user in your database
    # For this example, we'll just return a success message
    return jsonify({"message": "User registered successfully"}), 201

# User login endpoint
@app.route('/login', methods=['POST'])
@limiter.limit("10 per minute")
def login():
    try:
        data = LoginSchema().load(request.json)
    except ValidationError as err:
        return jsonify(err.messages), 400

    # This would typically involve checking credentials against your database
    # For this example, we'll just create a token
    token = jwt.encode({
        'user_id': data['username'],
        'exp': datetime.utcnow() + timedelta(seconds=app.config['JWT_EXPIRATION_DELTA'])
    }, app.config['SECRET_KEY'], algorithm="HS256")
    return jsonify({'token': token})

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0')
