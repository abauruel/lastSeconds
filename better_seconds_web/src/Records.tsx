import { useState, useRef, useEffect } from 'react'
import axios from "axios";
import { SERVER_HOST, FILES_PORT } from './config';

import './App.css'

const FILES_BASE_URL = `http://${SERVER_HOST}:${FILES_PORT}`;

type VideoProps = {
  name: string,
  thumbnail: string,
  url: string
}

export function Records() {
  const [videos, setVideos] = useState<VideoProps[]>([]);

  async function handleDeleteFile(filename: string) {
    const answer = confirm("Você tem certeza que deseja deletar o arquivo?")
    if (!answer) return

    try {

      const response = await axios.delete(`${FILES_BASE_URL}/api/download/${filename}`);
      if (response.status === 200) {
        setVideos((prevVideos) => prevVideos.filter((video) => video.name !== filename));
        console.log("Arquivo deletado com sucesso");
      } else {
        console.error("Erro ao deletar o arquivo:", response.statusText);
      }
    } catch (error) {
      console.error("Erro ao buscar vídeos:", error);
    }
  }

  useEffect(() => {
    const fetchVideos = async () => {
      try {
        const response = await axios.get(`${FILES_BASE_URL}/api/videos`);
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
            <a href={`${FILES_BASE_URL}${video.thumbnail.replace('.jpeg', '')}`} target="_blank">

              <img

                src={`${FILES_BASE_URL}${video.thumbnail}`}
                alt={video.name}
                style={{ width: "150px", height: "auto", marginRight: "10px", borderRadius: "10px" }}
              />
            </a>
            <div className='video-details' style={{ display: "flex", flexDirection: "column", alignItems: "start", justifyContent: "center" }}>
              <p ><a href={`${FILES_BASE_URL}${video.thumbnail.replace('.jpeg', '')}`} target="_blank">{video.name}</a></p>
              <div className='flex flex-row gap-2'>

                <a href={`${FILES_BASE_URL}${video.url}`} download>

                  <button className='download-btn'>Download</button>

                </a>
                <button className='text-red-600 border-red-600' onClick={() => handleDeleteFile(video.name)}>delete</button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div >
  )
}

