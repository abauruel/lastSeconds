import axios from "axios"
import { useEffect, useRef, useState } from "react"
import { Route, useNavigate } from "react-router"
import Hls from 'hls.js'
import { useRecording } from "./context/RecordingContext";

export function Configure() {
  const { isRecording, setIsRecording } = useRecording();

  const [enableCamera, setEnableCamera] = useState(false)
  // const [isRecording, setIsRecording] = useState(false)
  const [isBuffering, setIsBuffering] = useState(false)

  const videoRef1 = useRef<HTMLVideoElement>(null)
  const videoRef2 = useRef<HTMLVideoElement>(null)
  const [imgSrc1, setImagSrc1] = useState("http://bettersecond.local:8888/live/stream1/stream.m3u8")
  const [imgSrc2, setImagSrc2] = useState("http://bettersecond.local:8888/live/stream2/stream.m3u8")


  const navigate = useNavigate()

  async function handleConfigure() {
    // const response = await axios.post("http://bettersecond.local:5000/configure", {
    //   configure: !enableCamera
    // })
    // const { message } = response.data
    // if (message.match("enableD")) {
    //   setEnableCamera(true)
    navigate('/Cameras')

    // } else {
    //   setEnableCamera(false)
    // }

  }

  async function handleRecord() {
    setIsRecording(true)

    await axios.post("http://bettersecond.local:5000/start")

  }

  async function handleStopRecord() {
    setIsRecording(false);

    await axios.post("http://bettersecond.local:5000/stop")
  }

  async function handleCleanBuffers() {
    const answer = confirm("Você tem certeza que deseja limpar os buffers?")
    if (!answer) {
      return
    } else {
      await axios.post("http://bettersecond.local:5000/clear_buffers")
    }
  }

  async function handleRegisterBuffer() {
    setIsBuffering(true)
    await axios.post("http://bettersecond.local:5000/record")
    setTimeout(() => {
      setIsBuffering(false)
    }, 3000)
  }

  useEffect(() => {
    if (Hls.isSupported()) {
      const hls1 = new Hls()
      const hls2 = new Hls()

      hls1.on(Hls.Events.ERROR, (event, data) => {
        console.error('HLS Error (Stream 1):', data)
      })

      hls2.on(Hls.Events.ERROR, (event, data) => {
        console.error('HLS Error (Stream 2):', data)
      })


      if (videoRef1.current) {
        hls1.loadSource(imgSrc1)
        hls1.attachMedia(videoRef1.current)
      }

      if (videoRef2.current) {
        hls2.loadSource(imgSrc2)
        hls2.attachMedia(videoRef2.current)
      }

      return () => {
        hls1.destroy()
        hls2.destroy()
      }
    }
  }, [imgSrc1, imgSrc2])

  return (
    <>
      <h2>Visualizador de imagens </h2>

      <br />

      <div className='flex flex-row flex-wrap gap-1'>
        <video ref={videoRef1} autoPlay playsInline className='w-96 -scale-x-100' />
        <video ref={videoRef2} autoPlay playsInline className='w-96 -scale-x-100' />
      </div>

      {!enableCamera && (

        <div className="flex flex-col mt-4 mb-2">

          <p className="">Iniciar Registro</p>
          <div className="flex flex-row h-8 gap-3 mt-2 w-full">
            <button className={`flex  items-center ${isRecording ? 'animate-blinking bg-red-500 disabled:opacity-75' : 'bg-green-500'}
        `} onClick={handleRecord}> {isRecording ? "Gravando" : "Iniciar"}</button>
            {isRecording && (
              <button className="bg-orange-400 flex items-center" onClick={handleRegisterBuffer}>{isBuffering ? 'salvando...' : 'Salvar jogada'}</button>
            )}
            <button className="bg-slate-500 flex items-center" onClick={handleStopRecord}> Parar</button>
            <button className="bg-red-500 flex items-center" onClick={handleCleanBuffers}> Limpar buffers</button>
          </div>
          <a className="mt-2 " href="/records">minhas gravações</a>
        </div>
      )}
    </>
  )
}

