import React, { useState, useEffect } from 'react';
import axios from 'axios';
import VideoPlayer from './components/VideoPlayer';
import VideoUploader from './components/VideoUploader';
import VideoList from './components/VideoList';
import './App.css';

const API_URL = 'http://localhost:5000/api';

function App() {
  const [selectedVideo, setSelectedVideo] = useState(null);
  const [processing, setProcessing] = useState(false);
  const [videos, setVideos] = useState([]);
  const [error, setError] = useState('');

  useEffect(() => {
    // Загружаем список обработанных видео при запуске приложения
    fetchVideos();
  }, []);

  const fetchVideos = async () => {
    try {
      const response = await axios.get(`${API_URL}/videos`);
      setVideos(response.data);
    } catch (err) {
      console.error('Ошибка при загрузке списка видео:', err);
      setError('Не удалось загрузить список видео');
    }
  };

  const handleVideoUpload = async (file) => {
    setProcessing(true);
    setError('');
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
      const response = await axios.post(`${API_URL}/upload`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });
      
      if (response.data.status === 'success') {
        // Обновляем список видео после успешной обработки
        fetchVideos();
        
        // Выбираем только что обработанное видео
        setSelectedVideo({
          video: response.data.video,
          subtitles: response.data.subtitles
        });
      }
    } catch (err) {
      console.error('Ошибка при загрузке видео:', err);
      setError(err.response?.data?.error || 'Произошла ошибка при загрузке и обработке видео');
    } finally {
      setProcessing(false);
    }
  };

  const handleVideoSelect = (video) => {
    setSelectedVideo(video);
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>Система распознавания речи</h1>
      </header>
      
      <main className="App-main">
        <div className="App-sidebar">
          <VideoUploader onUpload={handleVideoUpload} disabled={processing} />
          
          <div className="Videos-list-container">
            <h2>Обработанные видео</h2>
            <VideoList videos={videos} onSelect={handleVideoSelect} />
          </div>
        </div>
        
        <div className="App-content">
          {processing ? (
            <div className="Processing-indicator">
              <p>Обработка видео... Это может занять несколько минут.</p>
            </div>
          ) : selectedVideo ? (
            <VideoPlayer 
              videoUrl={`http://localhost:5000${selectedVideo.video}`} 
              subtitlesUrl={`http://localhost:5000${selectedVideo.subtitles}`} 
            />
          ) : (
            <div className="No-video-placeholder">
              <p>Загрузите видео или выберите из списка для просмотра с субтитрами</p>
            </div>
          )}
          
          {error && <div className="Error-message">{error}</div>}
        </div>
      </main>
    </div>
  );
}

export default App;
