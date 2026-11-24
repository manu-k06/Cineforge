import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import './index.css'
import App from './App.jsx'
import { AuthProvider } from './context/AuthContext'
import { WatchHistoryProvider } from './context/WatchHistoryContext'
import { DialogProvider } from './context/DialogContext'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <WatchHistoryProvider>
          <DialogProvider>
            <App />
          </DialogProvider>
        </WatchHistoryProvider>
      </AuthProvider>
    </BrowserRouter>
  </StrictMode>,
)

