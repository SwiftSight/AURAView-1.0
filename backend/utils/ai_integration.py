# utils/ai_integration.py

import os
import logging
import numpy as np
import open3d as o3d
from google.cloud import aiplatform

def ai_assisted_completion(pcd):
    try:
        # Convert point cloud to numpy array
        points = np.asarray(pcd.points)

        # Initialize AI Platform client
        project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
        endpoint_id = os.getenv('VERTEX_AI_ENDPOINT_ID')
        location = os.getenv('VERTEX_AI_LOCATION', 'us-central1')

        client_options = {"api_endpoint": f"{location}-aiplatform.googleapis.com"}
        client = aiplatform.gapic.PredictionServiceClient(client_options=client_options)

        # Prepare the instance for prediction
        instances = [points.tolist()]
        endpoint = client.endpoint_path(project=project_id, location=location, endpoint=endpoint_id)

        # Send prediction request
        response = client.predict(endpoint=endpoint, instances=instances)
        predicted_points = response.predictions[0]

        # Create enhanced point cloud
        enhanced_pcd = o3d.geometry.PointCloud()
        enhanced_pcd.points = o3d.utility.Vector3dVector(np.array(predicted_points))

        # Estimate normals
        enhanced_pcd.estimate_normals()

        return enhanced_pcd
    except Exception as e:
        logging.error(f'Error in ai_assisted_completion: {e}', exc_info=True)
        return pcd  # Return the original point cloud in case of failure
