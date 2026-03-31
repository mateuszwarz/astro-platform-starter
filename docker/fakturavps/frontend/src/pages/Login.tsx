import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { Zap, Lock, Mail, AlertCircle } from 'lucide-react'
import { useAuth } from '../context/AuthContext'

interface LoginForm {
  email: string
  password: string
}

export default function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  const { register, handleSubmit, formState: { errors } } = useForm<LoginForm>()

  const onSubmit = async (data: LoginForm) => {
    setError('')
    setIsLoading(true)
    try {
      await login(data.email, data.password)
      navigate('/dashboard')
    } catch (err: unknown) {
      const message = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setError(message || 'Błąd logowania. Sprawdź dane i spróbuj ponownie.')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-blue-900 to-slate-900 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-blue-600 rounded-2xl shadow-lg mb-4">
            <Zap size={32} className="text-white" />
          </div>
          <h1 className="text-3xl font-bold text-white">FakturaVPS</h1>
          <p className="text-blue-200 mt-1">System zarządzania fakturami</p>
        </div>

        <div className="bg-white rounded-2xl shadow-2xl p-8">
          <h2 className="text-xl font-bold text-gray-900 mb-6">Zaloguj się</h2>

          {error && (
            <div className="flex items-center gap-3 p-4 bg-red-50 border border-red-200 rounded-lg mb-6">
              <AlertCircle size={18} className="text-red-500 shrink-0" />
              <p className="text-sm text-red-700">{error}</p>
            </div>
          )}

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">
                Adres email
              </label>
              <div className="relative">
                <Mail size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                <input
                  type="email"
                  placeholder="admin@faktura.pl"
                  {...register('email', { required: 'Email jest wymagany' })}
                  className="input-field pl-10"
                />
              </div>
              {errors.email && <p className="text-red-500 text-xs mt-1">{errors.email.message}</p>}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">
                Hasło
              </label>
              <div className="relative">
                <Lock size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                <input
                  type="password"
                  placeholder="••••••••"
                  {...register('password', { required: 'Hasło jest wymagane' })}
                  className="input-field pl-10"
                />
              </div>
              {errors.password && <p className="text-red-500 text-xs mt-1">{errors.password.message}</p>}
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full py-3 bg-blue-600 text-white font-semibold rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {isLoading ? (
                <>
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  Logowanie...
                </>
              ) : (
                'Zaloguj się'
              )}
            </button>
          </form>

          <p className="text-xs text-gray-400 mt-6 text-center">
            Dane demo: admin@faktura.pl / Admin123!
          </p>
        </div>
      </div>
    </div>
  )
}
