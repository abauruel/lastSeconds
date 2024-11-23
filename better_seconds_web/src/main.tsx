import React from 'react'
import ReactDOM from 'react-dom/client'
import { Records } from './Records.tsx'
import { Configure } from './Configure.tsx'
import './index.css'
import { BrowserRouter, Route, Routes } from 'react-router'
import { Cameras } from './Cameras.tsx'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path='/' element={<Configure />} />
        <Route path='/records' element={<Records />} />
        <Route path='/Cameras' element={<Cameras />} />
      </Routes>
    </BrowserRouter>
  </React.StrictMode>,
)
