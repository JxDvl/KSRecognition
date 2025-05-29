import React, { useRef, useState } from 'react';

function VideoUploader({ onUpload, disabled }) {
  const fileInputRef = useRef(null);
  const [selectedFile, setSelectedFile] = useState(null);

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      setSelectedFile(file);
    }
  };

  const handleUploadClick = () => {
    if (selectedFile) {
      onUpload(selectedFile);
      setSelectedFile(null);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleButtonClick = () => {
    fileInputRef.current.click();
  };

  return (
    <div className="video-uploader">
      <h2>Загрузить новое видео</h2>
      <div className="file-input-container">
        <input
          type="file"
          ref={fileInputRef}
          style={{ display: 'none' }}
          accept="video/mp4,video/avi,video/mov,video/mkv,video/quicktime,.mp4,.avi,.mov,.MOV,.mkv,.MP4,.AVI,.MKV"
          onChange={handleFileChange}
          disabled={disabled}
        />
        <button 
          className="select-file-button" 
          onClick={handleButtonClick}
          disabled={disabled}
        >
          Выбрать файл
        </button>
        {selectedFile && (
          <div className="selected-file">
            <p>{selectedFile.name}</p>
            <button 
              className="upload-button" 
              onClick={handleUploadClick}
              disabled={disabled}
            >
              Загрузить и обработать
            </button>
          </div>
        )}
        {disabled && <p>Обработка видео...</p>}
      </div>
    </div>
  );
}

export default VideoUploader; 