import { useState, useRef, useEffect } from 'react'
import axios from "axios";

import './App.css'

const backend_ip = 'bettersecond'

type VideoProps = {
  name: string,
  thumbnail: string,
  url: string
}

export function Records() {
  const [videos, setVideos] = useState<VideoProps[]>([]);

  useEffect(() => {
    const fetchVideos = async () => {
      try {
        const response = await axios.get(`http://${backend_ip}:3333/api/videos`);
        setVideos(response.data);
      } catch (error) {
        console.error("Erro ao buscar vídeos:", error);
      }
    };
    fetchVideos();
  }, []);


  return (

    <div className='container'>
      <h2>Registro de gravações</h2>
      <a href="/">voltar</a>
      <div style={{ display: "flex", flexDirection: "column", gap: "10px", }}>
        {videos?.map((video) => (
          <div key={video.name} style={{ display: "flex", alignItems: "center" }} className='video-item video-thumbnail'>
            <img

              src={`http://${backend_ip}:3333${video.thumbnail}`}
              alt={video.name}
              style={{ width: "150px", height: "auto", marginRight: "10px", borderRadius: "10px" }}
            />
            <div className='video-details' style={{ display: "flex", flexDirection: "column", alignItems: "start", justifyContent: "center" }}>
              <p ><a href={`http://${backend_ip}:3333${video.thumbnail.replace('.png', '')}`} target="_blank">{video.name}</a></p>
              <a href={`http://${backend_ip}:3333${video.url}`} download>
                <button className='download-btn'>Download</button>
              </a>
            </div>
          </div>
        ))}
      </div>
    </div >
  )
}

