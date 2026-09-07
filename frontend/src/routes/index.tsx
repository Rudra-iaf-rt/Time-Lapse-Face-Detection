import { Navigate, Route, Routes } from 'react-router-dom'
import type { ReactNode } from 'react'
import { useAuth } from '@/store/auth'
import { AppLayout } from '@/layouts/AppLayout'
import { LoginPage } from '@/pages/LoginPage'
import { DashboardPage } from '@/pages/DashboardPage'
import { LiveMonitoringPage } from '@/pages/LiveMonitoringPage'
import { PersonsPage } from '@/pages/PersonsPage'
import { PersonDetailPage } from '@/pages/PersonDetailPage'
import { TimelinePage } from '@/pages/TimelinePage'
import { SearchPage } from '@/pages/SearchPage'
import { CamerasPage } from '@/pages/CamerasPage'
import { TopologyPage } from '@/pages/TopologyPage'
import { BehaviorPage } from '@/pages/BehaviorPage'
import { AnomaliesPage } from '@/pages/AnomaliesPage'
import { CrowdPage } from '@/pages/CrowdPage'
import { SystemHealthPage } from '@/pages/SystemHealthPage'
import { AdminPage } from '@/pages/AdminPage'

function Protected({ children }: { children: ReactNode }) {
  const { isAuthenticated } = useAuth()
  if (!isAuthenticated) return <Navigate to="/login" replace />
  return children
}

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/"
        element={
          <Protected>
            <AppLayout />
          </Protected>
        }
      >
        <Route index element={<DashboardPage />} />
        <Route path="live" element={<LiveMonitoringPage />} />
        <Route path="persons" element={<PersonsPage />} />
        <Route path="persons/:globalId" element={<PersonDetailPage />} />
        <Route path="timeline" element={<TimelinePage />} />
        <Route path="search" element={<SearchPage />} />
        <Route path="cameras" element={<CamerasPage />} />
        <Route path="topology" element={<TopologyPage />} />
        <Route path="behavior" element={<BehaviorPage />} />
        <Route path="anomalies" element={<AnomaliesPage />} />
        <Route path="crowd" element={<CrowdPage />} />
        <Route path="health" element={<SystemHealthPage />} />
        <Route path="admin" element={<AdminPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
