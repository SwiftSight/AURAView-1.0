// UploadForm.js

import React, { useState } from 'react';

function UploadForm() {
    const [file, setFile] = useState(null);

    const handleSubmit = (event) => {
        event.preventDefault();
        if (!file) return;

        const formData = new FormData();
        formData.append('file', file);

        fetch('/api/v1/uploads', {
            method: 'POST',
            body: formData,
        })
            .then(response => response.json())
            .then(data => {
                alert(data.message || 'File uploaded successfully');
            })
            .catch(error => {
                console.error('Error:', error);
                alert('File upload failed');
            });
    };

    return (
        <form onSubmit={handleSubmit}>
            <label>
                Upload Model File:
                <input type="file" onChange={e => setFile(e.target.files[0])} accept=".ply,.pcd,.sensor" />
            </label>
            <button type="submit">Upload</button>
        </form>
    );
}

export default UploadForm;
