import axios from 'axios'
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router'
export function Cameras() {
  const navigate = useNavigate()

  const [imgSrc1, setImagSrc1] = useState("http://bettersecond:5000/stream/0")
  const [imgSrc2, setImagSrc2] = useState("http://bettersecond:5000/stream/2")

  async function handleClose() {
    setImagSrc1("")
    setImagSrc2("")

    const response = await axios.post("http://bettersecond:5000/configure", {
      configure: false
    })
    navigate("/")
  }

  return (
    <div className="flex flex-col">
      <button onClick={handleClose}>Fechar</button>
      <img src={imgSrc1} />
      <img src={imgSrc2} />
    </div>
  )
}