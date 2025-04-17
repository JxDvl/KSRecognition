import React from 'react';

function VideoList({ videos, onSelect }) {
  if (!videos.length) {
    return <p>Нет обработанных видео</p>;
  }

  return (
    <div className="videos-list">
      <ul>
        {videos.map((video, index) => (
          <li key={index} onClick={() => onSelect(video)}>
            {video.name}
          </li>
        ))}
      </ul>
    </div>
  );
}

export default VideoList; 