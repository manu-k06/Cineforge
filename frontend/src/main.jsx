import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'
import { AuthProvider } from './context/AuthContext'
import { WatchHistoryProvider } from './context/WatchHistoryContext'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <AuthProvider>
      <WatchHistoryProvider>
        <App />
      </WatchHistoryProvider>
    </AuthProvider>
  </StrictMode>,
)

