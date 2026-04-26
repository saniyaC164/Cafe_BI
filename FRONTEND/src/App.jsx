import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import Login from './pages/Login'
import Overview from './pages/Overview'
import KpiPage from './pages/KpiPage'
import MbaPage from './pages/MbaPage'
import SentimentPage from './pages/SentimentPage'
import ForecastingPage from './pages/ForecastingPage'
import InventoryPage from './pages/InventoryPage'

function PrivateRoute({ children }) {
  const token = localStorage.getItem('token')
  return token ? children : <Navigate to="/login" replace />
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route element={
          <PrivateRoute>
            <Layout />
          </PrivateRoute>
        }>
          <Route index element={<Overview />} />
          <Route path="kpi" element={<KpiPage />} />
          <Route path="market-basket" element={<MbaPage />} />
          <Route path="sentiment" element={<SentimentPage />} />
          <Route path="forecasting" element={<ForecastingPage />} />
          <Route path="inventory" element={<InventoryPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}