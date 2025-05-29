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
  const [loadingSubtitles, setLoadingSubtitles] = useState(true);
  const overlayRef = useRef(null);
  
  useEffect(() => {
    const fetchSubtitles = async () => {
      if (!subtitlesUrl) return;
      
      setLoadingSubtitles(true);
      console.log("Загрузка субтитров из:", subtitlesUrl);
      
      try {
        const response = await axios.get(subtitlesUrl);
        console.log("Получен ответ:", response);
        console.log("Тип данных ответа:", typeof response.data);
        
        if (response.data && Array.isArray(response.data) && response.data.length > 0) {
          console.log("Получены субтитры:", response.data.length, "элементов", response.data[0]);
          setSubtitles(response.data);
        } else {
          console.error("Некорректный формат субтитров:", response.data);
          setSubtitles([]);
        }
        setLoadingSubtitles(false);
      } catch (err) {
        console.error('Ошибка при загрузке субтитров:', err);
        setLoadingSubtitles(false);
        setSubtitles([]);
      }
    };
    
    if (subtitlesUrl) {
      fetchSubtitles();
    }
  }, [subtitlesUrl]);
  
  useEffect(() => {
    console.log("VideoPlayer получил URL:", videoUrl);
  }, [videoUrl]);
  
  useEffect(() => {
    if (subtitles && subtitles.length > 0) {
      const activeSubtitle = subtitles.find(
        sub => currentTime >= sub.start && currentTime <= sub.end
      );
      
      if (activeSubtitle !== currentSubtitle) {
        setCurrentSubtitle(activeSubtitle);
        if (activeSubtitle) {
          console.log("Активный субтитр:", activeSubtitle.text.substring(0, 30) + "...");
        }
      }
    }
  }, [currentTime, subtitles, currentSubtitle]);
  
  useEffect(() => {
    if (playerRef.current) {
      try {
        const videoElement = playerRef.current.getInternalPlayer();
        if (videoElement) {
          console.log("Доступ к video элементу:", videoElement);
          
          const handleFullScreenChange = () => {
            const isNowFullscreen = document.fullscreenElement === videoElement 
              || document.webkitFullscreenElement === videoElement;
            
            console.log("Video fullscreen event:", isNowFullscreen);
            
            if (overlayRef.current) {
              overlayRef.current.style.zIndex = isNowFullscreen ? "9999" : "10";
            }
          };
          
          videoElement.addEventListener('fullscreenchange', handleFullScreenChange);
          videoElement.addEventListener('webkitfullscreenchange', handleFullScreenChange);
          
          return () => {
            videoElement.removeEventListener('fullscreenchange', handleFullScreenChange);
            videoElement.removeEventListener('webkitfullscreenchange', handleFullScreenChange);
          };
        }
      } catch (err) {
        console.error("Ошибка при доступе к видео элементу:", err);
      }
    }
  }, [playerRef.current]);
  
  useEffect(() => {
    const checkFullscreen = () => {
      const isFullscreenNow = !!(
        document.fullscreenElement ||
        document.webkitFullscreenElement ||
        document.mozFullScreenElement ||
        document.msFullscreenElement
      );
      
      console.log("Fullscreen state changed:", isFullscreenNow);
      setIsFullscreen(isFullscreenNow);
      
      if (isFullscreenNow && overlayRef.current) {
        try {
          const fullscreenElement = 
            document.fullscreenElement || 
            document.webkitFullscreenElement || 
            document.mozFullScreenElement || 
            document.msFullscreenElement;
            
          if (fullscreenElement) {
            console.log("Перемещение субтитров в полноэкранный режим");
          }
        } catch (err) {
          console.error("Ошибка при манипуляции с DOM в fullscreen:", err);
        }
      }
    };
    
    document.addEventListener('fullscreenchange', checkFullscreen);
    document.addEventListener('webkitfullscreenchange', checkFullscreen);
    document.addEventListener('mozfullscreenchange', checkFullscreen);
    document.addEventListener('MSFullscreenChange', checkFullscreen);
    
    checkFullscreen();
    
    return () => {
      document.removeEventListener('fullscreenchange', checkFullscreen);
      document.removeEventListener('webkitfullscreenchange', checkFullscreen);
      document.removeEventListener('mozfullscreenchange', checkFullscreen);
      document.removeEventListener('MSFullscreenChange', checkFullscreen);
    };
  }, []);
  
  const handleProgress = (state) => {
    if (state && typeof state.playedSeconds === 'number') {
      setCurrentTime(state.playedSeconds);
    }
  };
  
  const handleSeek = (seconds) => {
    setCurrentTime(seconds);
  };
  
  const handleSubtitleClick = (subtitle) => {
    if (playerRef.current) {
      try {
        console.log(`Переход к таймкоду: ${subtitle.start}s`);
        playerRef.current.seekTo(parseFloat(subtitle.start), 'seconds');
      } catch (e) {
        console.error("Ошибка при перемотке видео:", e);
      }
    }
  };
  
  const toggleFullscreen = () => {
    if (!containerRef.current) return;
    
    if (!isFullscreen) {
      if (containerRef.current.requestFullscreen) {
        containerRef.current.requestFullscreen().catch(err => {
          console.error("Ошибка при переходе в полноэкранный режим:", err);
        });
      } else if (containerRef.current.webkitRequestFullscreen) {
        containerRef.current.webkitRequestFullscreen();
      } else if (containerRef.current.mozRequestFullScreen) {
        containerRef.current.mozRequestFullScreen();
      } else if (containerRef.current.msRequestFullscreen) {
        containerRef.current.msRequestFullscreen();
      }
    } else {
      if (document.exitFullscreen) {
        document.exitFullscreen();
      } else if (document.webkitExitFullscreen) {
        document.webkitExitFullscreen();
      } else if (document.mozCancelFullScreen) {
        document.mozCancelFullScreen();
      } else if (document.msExitFullscreen) {
        document.msExitFullscreen();
      }
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
            playsinline
            onEnded={() => console.log("Видео завершено")}
            onPlay={() => console.log("Видео воспроизводится")}
            onPause={() => console.log("Видео на паузе")}
            onBuffer={() => console.log("Видео буферизуется")}
            onBufferEnd={() => console.log("Видео закончило буферизацию")}
            onError={(e) => console.error("Ошибка воспроизведения видео:", e)}
            config={{
              file: {
                attributes: {
                  controlsList: 'nodownload',
                  disablePictureInPicture: true,
                  style: { position: 'absolute', top: 0, left: 0, width: '100%', height: '100%' },
                },
                forceVideo: true,
                forceSafariHLS: true,
                forceHLS: false,
                hlsOptions: {
                  enableWorker: true,
                  lowLatencyMode: true,
                },
              },
              youtube: {
                playerVars: {
                  modestbranding: 1,
                  rel: 0,
                  showinfo: 0,
                  iv_load_policy: 3,
                }
              }
            }}
          />
          
          {currentSubtitle && (
            <div 
              className="overlay-subtitle" 
              ref={overlayRef}
              style={{ zIndex: isFullscreen ? 9999 : 10 }}
            >
              <div className="subtitle-text-overlay">
                {currentSubtitle.text}
              </div>
            </div>
          )}
          
          {/* Дополнительная кнопка переключения полноэкранного режима */}
          <button 
            className="fullscreen-button" 
            onClick={toggleFullscreen}
            style={{
              position: 'absolute',
              right: '10px',
              bottom: '10px',
              padding: '5px',
              background: 'rgba(0, 0, 0, 0.5)',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
              zIndex: 1000,
              display: 'none' // Скрыл ее, так как использовал встроенные инструменты, но она нужна на случай с другими браузерами
            }}
          >
            {isFullscreen ? 'Выйти из полноэкранного режима' : 'Полноэкранный режим'}
          </button>
        </div>
      </div>
      
      <div className="subtitles-list">
        <h3>Все субтитры</h3>
        {loadingSubtitles ? (
          <div className="loading-subtitles">Загрузка субтитров...</div>
        ) : subtitles.length === 0 ? (
          <div className="no-subtitles">Субтитры не найдены</div>
        ) : (
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
        )}
      </div>
    </div>
  );
}

function formatTime(seconds) {
  if (typeof seconds !== 'number') {
    console.warn("formatTime получил некорректное значение:", seconds);
    seconds = 0;
  }
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs < 10 ? '0' : ''}${secs}`;
}

export default VideoPlayer; 