import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import { ProtectedRoute } from './components/ProtectedRoute'
import { Layout } from './components/Layout'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import InvoiceList from './pages/invoices/InvoiceList'
import InvoiceDetail from './pages/invoices/InvoiceDetail'
import InvoiceForm from './pages/invoices/InvoiceForm'
import ContractorList from './pages/contractors/ContractorList'
import ContractorForm from './pages/contractors/ContractorForm'
import PaymentList from './pages/payments/PaymentList'
import Reports from './pages/reports/Reports'
import EmailSources from './pages/email/EmailSources'
import EmailLog from './pages/email/EmailLog'
import BankStatements from './pages/bank/BankStatements'

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <Layout />
              </ProtectedRoute>
            }
          >
            <Route index element={<Navigate to="/dashboard" replace />} />
            <Route path="dashboard" element={<Dashboard />} />
            <Route path="faktury" element={<InvoiceList />} />
            <Route path="faktury/nowa" element={<InvoiceForm />} />
            <Route path="faktury/:id" element={<InvoiceDetail />} />
            <Route path="faktury/:id/edytuj" element={<InvoiceForm />} />
            <Route path="kontrahenci" element={<ContractorList />} />
            <Route path="kontrahenci/nowy" element={<ContractorForm />} />
            <Route path="kontrahenci/:id/edytuj" element={<ContractorForm />} />
            <Route path="platnosci" element={<PaymentList />} />
            <Route path="raporty" element={<Reports />} />
            <Route path="poczta" element={<EmailSources />} />
            <Route path="poczta/log" element={<EmailLog />} />
            <Route path="wyciagi" element={<BankStatements />} />
          </Route>
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  )
}

export default App
