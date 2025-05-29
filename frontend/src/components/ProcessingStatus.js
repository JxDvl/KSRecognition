import React, { useState, useEffect, useRef } from 'react';
import ReactPlayer from 'react-player';
import './ProcessingStatus.css';

function ProcessingStatus({ status, videoUrl }) {
  const [currentTime, setCurrentTime] = useState(0);
  const [currentSubtitle, setCurrentSubtitle] = useState(null);
  const [startTime, setStartTime] = useState(Date.now());
  const [elapsedTime, setElapsedTime] = useState(0);
  const playerRef = useRef(null);
  const timerRef = useRef(null);
  

  useEffect(() => {
    setStartTime(Date.now());
    
    timerRef.current = setInterval(() => {
      setElapsedTime(Math.floor((Date.now() - startTime) / 1000));
    }, 1000);
    
    return () => clearInterval(timerRef.current);
  }, [startTime]);
  
  useEffect(() => {
    if (status?.partial_subtitles && status.partial_subtitles.length > 0) {
      console.log(`Получены субтитры (${status.partial_subtitles.length} шт.):`, 
                  status.partial_subtitles.slice(0, 1)); // Выводим только первый для краткости
    }
  }, [status?.partial_subtitles]);
  
  useEffect(() => {
    if (status?.partial_subtitles && status.partial_subtitles.length > 0) {
      const activeSubtitle = status.partial_subtitles.find(
        sub => currentTime >= sub.start && currentTime <= sub.end
      );
      
      if (activeSubtitle !== currentSubtitle) {
        setCurrentSubtitle(activeSubtitle);
        console.log("Активный субтитр:", activeSubtitle);
      }
    }
  }, [currentTime, status?.partial_subtitles, currentSubtitle]);
  
  const handleProgress = (state) => {
    if (state && typeof state.playedSeconds === 'number') {
      setCurrentTime(state.playedSeconds);
    }
  };
  
  const handleSubtitleClick = (subtitle) => {
    if (playerRef.current) {
      try {
        const player = playerRef.current.getInternalPlayer();
        if (player) {
          player.currentTime = subtitle.start;
          if (player.paused) {
            player.play().catch(e => console.error("Ошибка воспроизведения:", e));
          }
        }
      } catch (e) {
        console.error("Ошибка при перемотке видео:", e);
      }
    }
  };
  
  const getRemainingTime = () => {
    if (!status || !status.estimated_time) return 'Оценка времени...';
    
    const remaining = status.estimated_time * (100 - status.progress) / 100;
    if (remaining < 60) {
      return `Осталось примерно ${Math.ceil(remaining)} сек.`;
    } else {
      return `Осталось примерно ${Math.ceil(remaining / 60)} мин.`;
    }
  };
  
  const formatElapsedTime = () => {
    const minutes = Math.floor(elapsedTime / 60);
    const seconds = elapsedTime % 60;
    return `${minutes}:${seconds < 10 ? '0' : ''}${seconds}`;
  };
  
  const getProcessingSpeed = () => {
    if (!status || status.progress <= 0 || elapsedTime <= 0) return null;
    
    const percentPerSecond = status.progress / elapsedTime;
    
    if (percentPerSecond < 0.1) {
      return `${(percentPerSecond * 60).toFixed(1)}% в минуту`;
    } else {
      return `${percentPerSecond.toFixed(1)}% в секунду`;
    }
  };
  
  if (!status) {
    return (
      <div className="processing-container">
        <div className="processing-indicator">
          <p>Инициализация обработки видео...</p>
          <div className="progress-bar-container">
            <div className="progress-bar loading-animation" style={{ width: '5%' }}></div>
          </div>
        </div>
      </div>
    );
  }
  
  const hasVideoUrl = videoUrl && typeof videoUrl === 'string';
  console.log("URL видео для предварительного просмотра:", hasVideoUrl ? videoUrl : "отсутствует");
  
  return (
    <div className="processing-container">
      <div className="processing-indicator">
        <h2>Обработка видео</h2>
        <div className="stage-badge">{status.current_stage || 'Инициализация...'}</div>
        
        <div className="progress-bar-container">
          <div 
            className={`progress-bar ${status.progress < 100 ? 'pulse-animation' : ''}`} 
            style={{ width: `${status.progress}%` }}
          ></div>
        </div>
        
        <div className="progress-stats">
          <div className="progress-details">
            <span className="progress-value">{status.progress}% выполнено</span>
            <span className="progress-time">{getRemainingTime()}</span>
          </div>
          
          <div className="time-info">
            <span>Прошло: {formatElapsedTime()}</span>
            {getProcessingSpeed() && (
              <span>Скорость: {getProcessingSpeed()}</span>
            )}
          </div>
        </div>
      </div>
      
      {hasVideoUrl && (
        <div className="video-preview">
          <h3>Предварительный просмотр видео</h3>
          <ReactPlayer
            ref={playerRef}
            url={videoUrl}
            controls
            width="100%"
            height="350px"
            onProgress={handleProgress}
            progressInterval={100}
            config={{
              file: {
                attributes: {
                  controlsList: 'nodownload',
                  disablePictureInPicture: true
                }
              }
            }}
          />
          
          {currentSubtitle && (
            <div className="overlay-subtitle">
              <div className="subtitle-text-overlay">
                {currentSubtitle.text}
              </div>
            </div>
          )}
        </div>
      )}
      
      {status.partial_subtitles && status.partial_subtitles.length > 0 && (
        <div className="partial-subtitles">
          <h3>Предварительные субтитры ({status.partial_subtitles.length})</h3>
          <div className="subtitle-stats">
            {status.partial_subtitles.length > 0 && (
              <span>Общее время: {formatTime(status.partial_subtitles[status.partial_subtitles.length-1].end)}</span>
            )}
            <span className="subtitle-count">Обработано чанков: {status.partial_subtitles.length}</span>
          </div>
          
          <div className="subtitles-scroll">
            {status.partial_subtitles.map((subtitle, index) => (
              <div 
                key={index} 
                className={`subtitle-item ${currentSubtitle && currentSubtitle.id === subtitle.id ? 'active' : ''} ${index === status.partial_subtitles.length - 1 ? 'latest-subtitle' : ''}`}
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
      )}
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

export default ProcessingStatus; 