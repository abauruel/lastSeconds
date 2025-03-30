import React from 'react'
import ReactDOM from 'react-dom/client'
import { Records } from './Records.tsx'
import { Configure } from './Configure.tsx'
import './index.css'
import { BrowserRouter, Route, Routes } from 'react-router'
import { RecordingProvider } from './context/RecordingContext.tsx'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <RecordingProvider>
      <BrowserRouter>
        <Routes>

          <Route path='/' element={
            <Configure />
          } />
          <Route path='/records' element={<Records />} />

        </Routes>
      </BrowserRouter>
    </RecordingProvider>
  </React.StrictMode>,
)
