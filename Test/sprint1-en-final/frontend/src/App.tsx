import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import AppLayout from './layouts/AppLayout';
import LoginPage from './pages/LoginPage';
import ResidentOverviewPage from './pages/ResidentOverviewPage';
import ResidentDashboardPage from './pages/ResidentDashboardPage';
import AlertCentrePage from './pages/AlertCentrePage';
import ReportPage from './pages/ReportPage';
import ResidentManagementPage from './pages/ResidentManagementPage';
import { isLoggedIn } from './api/client';

function PrivateRoute({ children }: { children: React.ReactNode }) {
  return isLoggedIn() ? <>{children}</> : <Navigate to="/login" replace />;
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          element={
            <PrivateRoute>
              <AppLayout />
            </PrivateRoute>
          }
        >
          <Route path="/residents" element={<ResidentOverviewPage />} />
          <Route path="/residents/manage" element={<ResidentManagementPage />} />
          <Route path="/residents/:id/dashboard" element={<ResidentDashboardPage />} />
          <Route path="/alerts" element={<AlertCentrePage />} />
          <Route path="/reports/:residentId" element={<ReportPage />} />
        </Route>
        <Route path="*" element={<Navigate to="/residents" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
