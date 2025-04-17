import React, { useState, useEffect, useRef } from 'react';
import ReactPlayer from 'react-player';
import axios from 'axios';

function VideoPlayer({ videoUrl, subtitlesUrl }) {
  const [subtitles, setSubtitles] = useState([]);
  const [currentTime, setCurrentTime] = useState(0);
  const [currentSubtitle, setCurrentSubtitle] = useState(null);
  const playerRef = useRef(null);
  const containerRef = useRef(null);
  const [isFullscreen, setIsFullscreen] = useState(false);
  
  useEffect(() => {
    const fetchSubtitles = async () => {
      try {
        const response = await axios.get(subtitlesUrl);
        setSubtitles(response.data);
      } catch (err) {
        console.error('Ошибка при загрузке субтитров:', err);
      }
    };
    
    if (subtitlesUrl) {
      fetchSubtitles();
    }
  }, [subtitlesUrl]);
  
  useEffect(() => {
    // Находим текущие субтитры на основе текущего времени видео
    if (subtitles.length > 0) {
      const activeSubtitle = subtitles.find(
        sub => currentTime >= sub.start && currentTime <= sub.end
      );
      
      if (activeSubtitle !== currentSubtitle) {
        setCurrentSubtitle(activeSubtitle);
      }
    }
  }, [currentTime, subtitles, currentSubtitle]);
  
  // Проверяем, находится ли плеер в полноэкранном режиме
  useEffect(() => {
    const checkFullscreen = () => {
      const isFullscreenNow = !!(
        document.fullscreenElement ||
        document.webkitFullscreenElement ||
        document.mozFullScreenElement ||
        document.msFullscreenElement
      );
      setIsFullscreen(isFullscreenNow);
    };
    
    document.addEventListener('fullscreenchange', checkFullscreen);
    document.addEventListener('webkitfullscreenchange', checkFullscreen);
    document.addEventListener('mozfullscreenchange', checkFullscreen);
    document.addEventListener('MSFullscreenChange', checkFullscreen);
    
    return () => {
      document.removeEventListener('fullscreenchange', checkFullscreen);
      document.removeEventListener('webkitfullscreenchange', checkFullscreen);
      document.removeEventListener('mozfullscreenchange', checkFullscreen);
      document.removeEventListener('MSFullscreenChange', checkFullscreen);
    };
  }, []);
  
  const handleProgress = (state) => {
    setCurrentTime(state.playedSeconds);
  };
  
  const handleSeek = (seconds) => {
    setCurrentTime(seconds);
  };
  
  const handleSubtitleClick = (subtitle) => {
    if (playerRef.current) {
      playerRef.current.seekTo(subtitle.start);
    }
  };
  
  return (
    <div className="video-player-container">
      <div className="video-player-wrapper">
        <div 
          ref={containerRef} 
          className={`fixed-video-container ${isFullscreen ? 'fullscreen' : ''}`}
        >
          <ReactPlayer
            ref={playerRef}
            url={videoUrl}
            controls
            width="100%"
            height="100%"
            onProgress={handleProgress}
            onSeek={handleSeek}
            progressInterval={100}
          />
          
          {currentSubtitle && (
            <div className="overlay-subtitle">
              <div className="subtitle-text-overlay">
                {currentSubtitle.text}
              </div>
            </div>
          )}
        </div>
      </div>
      
      <div className="subtitles-list">
        <h3>Все субтитры</h3>
        <div className="subtitles-scroll">
          {subtitles.map((subtitle, index) => (
            <div 
              key={index} 
              className={`subtitle-item ${currentSubtitle && currentSubtitle.id === subtitle.id ? 'active' : ''}`}
              onClick={() => handleSubtitleClick(subtitle)}
            >
              <span className="subtitle-time">
                {formatTime(subtitle.start)} - {formatTime(subtitle.end)}
              </span>
              <p className="subtitle-text">{subtitle.text}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// Вспомогательная функция для форматирования времени
function formatTime(seconds) {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs < 10 ? '0' : ''}${secs}`;
}

export default VideoPlayer; 