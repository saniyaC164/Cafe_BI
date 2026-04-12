import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Overview from './pages/Overview'
import KpiPage from './pages/KpiPage'
import MbaPage from './pages/MbaPage'
import SentimentPage from './pages/SentimentPage'
import ForecastingPage from './pages/ForecastingPage'
import InventoryPage from './pages/InventoryPage'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
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