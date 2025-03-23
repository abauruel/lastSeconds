import axios from "axios"
import { useState } from "react"
import { Route, useNavigate } from "react-router"

export function Configure() {
  const [enableCamera, setEnableCamera] = useState(false)
  const [isRecording, setIsRecording] = useState(false)
  const [isBuffering, setIsBuffering] = useState(false)
  const navigate = useNavigate()

  async function handleConfigure() {
    const response = await axios.post("http://bettersecond.local:5000/configure", {
      configure: !enableCamera
    })
    const { message } = response.data
    if (message.match("enableD")) {
      setEnableCamera(true)
      navigate('/Cameras')

    } else {
      setEnableCamera(false)
    }

  }

  async function handleRecord() {
    setIsRecording(true)

    await axios.post("http://bettersecond.local:5000/start_capture")

  }

  async function handleStopRecord() {
    setIsRecording(false)

    await axios.post("http://bettersecond.local:5000/stop_capture")
  }

  async function handleRegisterBuffer() {
    setIsBuffering(true)
    await axios.post("http://bettersecond.local:5000/register_buffer")
    setTimeout(() => {
      setIsBuffering(false)
    }, 3000)
  }
  return (
    <>
      <h1>Configuração </h1>
      {!isRecording && (
        <button className=" bg-slate-500"
          onClick={handleConfigure}>Visualizar camera</button>
      )}
      <br />

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
          </div>
          <a className="mt-2 " href="/records">minhas gravações</a>
        </div>
      )}
    </>
  )
}

