import React, { useState, useEffect } from 'react';
import axios from 'axios';
import VideoPlayer from './components/VideoPlayer';
import VideoUploader from './components/VideoUploader';
import VideoList from './components/VideoList';
import ProcessingStatus from './components/ProcessingStatus';
import './App.css';

const API_URL = 'http://localhost:5000/api';

function App() {
  const [selectedVideo, setSelectedVideo] = useState(null);
  const [processing, setProcessing] = useState(false);
  const [videos, setVideos] = useState([]);
  const [error, setError] = useState('');
  const [processingStatus, setProcessingStatus] = useState(null);
  const [tempVideoUrl, setTempVideoUrl] = useState(null);
  const [failedAttempts, setFailedAttempts] = useState(0);

  useEffect(() => {
    fetchVideos();
    
    checkProcessingStatus();
  }, []);

  const checkProcessingStatus = async () => {
    try {
      const response = await axios.get(`${API_URL}/progress`);
      
      if (response.data.is_processing) {
        console.log("Обнаружена активная обработка видео:", response.data);
        setProcessing(true);
        setProcessingStatus(response.data);
      } else if (response.data.progress === 100 && response.data.video && response.data.subtitles) {
        console.log("Обнаружено обработанное видео:", response.data);
        setSelectedVideo({
          video: response.data.video,
          subtitles: response.data.subtitles
        });
      }
    } catch (err) {
      console.error("Ошибка при проверке статуса:", err);
    }
  };

  useEffect(() => {
    let intervalId;
    
    if (processing) {
      console.log("Запущен мониторинг прогресса обработки видео");
      
      intervalId = setInterval(async () => {
        try {
          const response = await axios.get(`${API_URL}/progress`);
          console.log("Статус обработки:", response.data);
          
          setFailedAttempts(0);
          
          setProcessingStatus(response.data);
          
          if (!response.data.is_processing) {
            clearInterval(intervalId);
            
            if (response.data.progress === 100 && response.data.video && response.data.subtitles) {
              console.log("Обработка завершена успешно. Загружаем видео:", response.data.video);
              
              setSelectedVideo({
                video: response.data.video,
                subtitles: response.data.subtitles
              });
              
              setProcessing(false);
              fetchVideos();
              
              if (tempVideoUrl) {
                URL.revokeObjectURL(tempVideoUrl);
                setTempVideoUrl(null);
              }
            } else if (response.data.progress === 0) {
              const errorMessage = response.data.current_stage || 'Произошла ошибка при обработке видео';
              console.error("Ошибка обработки:", errorMessage);
              
              setError(errorMessage);
              setProcessing(false);
              
              if (tempVideoUrl) {
                URL.revokeObjectURL(tempVideoUrl);
                setTempVideoUrl(null);
              }
            }
          }
        } catch (err) {
          console.error('Ошибка при получении статуса обработки:', err);
          
          setFailedAttempts(prev => prev + 1);
          
          if (failedAttempts >= 5) {
            clearInterval(intervalId);
            setError('Не удалось получить статус обработки видео. Сервер не отвечает.');
            setProcessing(false);
          }
        }
      }, 1000);
    } else {
      clearInterval(intervalId);
    }
    
    return () => {
      if (intervalId) clearInterval(intervalId);
      
      if (tempVideoUrl) {
        URL.revokeObjectURL(tempVideoUrl);
      }
    };
  }, [processing, tempVideoUrl, failedAttempts]);

  const fetchVideos = async () => {
    try {
      const response = await axios.get(`${API_URL}/videos`);
      console.log("Получен список видео:", response.data);
      setVideos(response.data);
    } catch (err) {
      console.error('Ошибка при загрузке списка видео:', err);
      setError('Не удалось загрузить список видео');
    }
  };

  const handleVideoUpload = async (file) => {
    setError('');
    setProcessingStatus(null);
    setSelectedVideo(null);
    setFailedAttempts(0);
    
    console.log("Загрузка файла:", file.name, "Размер:", (file.size / (1024 * 1024)).toFixed(2), "МБ");
    
    const tempUrl = URL.createObjectURL(file);
    setTempVideoUrl(tempUrl);
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
      setProcessing(true);
      
      console.log("Отправка файла на сервер...");
      const response = await axios.post(`${API_URL}/upload`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        },
        timeout: 30000
      });
      
      console.log("Ответ от сервера:", response.data);
      
      if (response.data.status === 'processing') {
        console.log("Файл принят на обработку");
      } else if (response.data.status === 'success') {
        console.log("Обработка завершена сразу после загрузки");
        setProcessing(false);
        fetchVideos();
        
        setSelectedVideo({
          video: response.data.video,
          subtitles: response.data.subtitles
        });
        
        URL.revokeObjectURL(tempUrl);
        setTempVideoUrl(null);
      }
    } catch (err) {
      console.error('Ошибка при загрузке видео:', err);
      const errorMessage = err.response?.data?.error || 'Произошла ошибка при загрузке и обработке видео';
      console.error("Детали ошибки:", errorMessage);
      
      setError(errorMessage);
      setProcessing(false);
      URL.revokeObjectURL(tempUrl);
      setTempVideoUrl(null);
    }
  };

  const handleVideoSelect = (video) => {
    console.log("Выбрано видео:", video);
    setSelectedVideo(video);
  };

  const renderVideoPlayer = () => {
    if (!selectedVideo || !selectedVideo.video || !selectedVideo.subtitles) {
      console.error("Не удается отобразить видео: отсутствуют необходимые данные", selectedVideo);
      return (
        <div className="Error-message">
          <h3>Ошибка загрузки видео</h3>
          <p>Не удается отобразить видео: отсутствуют необходимые данные</p>
          <p>Детали: {JSON.stringify(selectedVideo)}</p>
        </div>
      );
    }
    
    console.log("Отображение видеоплеера с URL:", selectedVideo.video, selectedVideo.subtitles);
    
    return (
      <VideoPlayer 
        videoUrl={`http://localhost:5000${selectedVideo.video}`} 
        subtitlesUrl={`http://localhost:5000${selectedVideo.subtitles}`} 
      />
    );
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>Система распознавания речи</h1>
        <a 
          href="https://translate.google.com/?sl=kk&tl=ru" 
          target="_blank" 
          rel="noopener noreferrer"
          className="translate-link"
        >
          Google Переводчик (каз-рус)
        </a>
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
            <ProcessingStatus 
              status={processingStatus} 
              videoUrl={tempVideoUrl}
            />
          ) : selectedVideo ? (
            renderVideoPlayer()
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
