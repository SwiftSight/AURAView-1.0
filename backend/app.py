# app.py

import os
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS
from google.cloud import storage, tasks_v2
from werkzeug.utils import secure_filename
from model_processing import process_model
from utils.sensor_input import parse_sensor_data
from utils.optimization import optimize_processing
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env')

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Configure logging
logging.basicConfig(level=logging.INFO)

# Google Cloud configuration
GOOGLE_CLOUD_PROJECT = os.getenv('GOOGLE_CLOUD_PROJECT')
GCS_BUCKET_NAME = os.getenv('GCS_BUCKET_NAME')
QUEUE_NAME = os.getenv('QUEUE_NAME')
QUEUE_LOCATION = os.getenv('QUEUE_LOCATION')

# Initialize clients
storage_client = storage.Client()
bucket = storage_client.bucket(GCS_BUCKET_NAME)
task_client = tasks_v2.CloudTasksClient()
queue_path = task_client.queue_path(GOOGLE_CLOUD_PROJECT, QUEUE_LOCATION, QUEUE_NAME)

@app.route('/api/v1/uploads', methods=['POST'])
def upload_file():
    try:
        file = request.files.get('file')
        if not file or file.filename == '':
            return jsonify({'error': 'No file provided'}), 400

        filename = secure_filename(file.filename)
        local_path = os.path.join('/tmp', filename)
        file.save(local_path)

        # Enqueue a task for model processing
        task_payload = {
            "filename": filename,
            "local_path": local_path
        }
        task = {
            "http_request": {
                "http_method": tasks_v2.HttpMethod.POST,
                "url": f"{request.host_url}api/v1/process-model",
                "body": json.dumps(task_payload).encode(),
                "headers": {
                    "Content-Type": "application/json",
                    "X-AppEngine-QueueName": QUEUE_NAME
                }
            }
        }
        task_client.create_task(parent=queue_path, task=task)
        return jsonify({'message': 'Model upload successful. Processing started.'}), 202
    except Exception as e:
        logging.error(f'Error in upload_file: {e}', exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/v1/process-model', methods=['POST'])
def process_model_task():
    try:
        # Verify request is from Cloud Tasks
        if request.headers.get('X-AppEngine-QueueName') != QUEUE_NAME:
            return jsonify({'error': 'Unauthorized'}), 403

        data = request.get_json()
        local_path = data.get('local_path')
        filename = data.get('filename')

        # Process the model
        processed_file_path = process_model(local_path, filename)

        # Upload the processed model to Cloud Storage
        blob = bucket.blob(f'models/{filename}')
        blob.upload_from_filename(processed_file_path)

        # Clean up temporary files
        os.remove(local_path)
        os.remove(processed_file_path)

        return jsonify({'message': 'Model processed successfully', 'url': blob.public_url}), 200
    except Exception as e:
        logging.error(f'Error in process_model_task: {e}', exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=8080)
