// ModelViewer.js

import React, { useState } from 'react';
import { OBJModel } from 'react-3d-viewer';

function ModelViewer() {
    const [modelUrl, setModelUrl] = useState('');

    const handleLoadModel = () => {
        // Logic to fetch the model URL from backend or Cloud Storage
        fetch('/api/v1/get-latest-model')
            .then(response => response.json())
            .then(data => {
                setModelUrl(data.url);
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Failed to load model');
            });
    };

    return (
        <div>
            <button onClick={handleLoadModel}>Load Processed Model</button>
            {modelUrl && (
                <div>
                    <OBJModel src={modelUrl} />
                </div>
            )}
        </div>
    );
}

export default ModelViewer;
