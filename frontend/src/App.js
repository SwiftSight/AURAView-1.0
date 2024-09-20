// App.js

import React from 'react';
import UploadForm from './components/UploadForm';
import ModelViewer from './components/ModelViewer';

function App() {
    return (
        <div className="App">
            <h1>AURAView System</h1>
            <UploadForm />
            <ModelViewer />
        </div>
    );
}

export default App;
