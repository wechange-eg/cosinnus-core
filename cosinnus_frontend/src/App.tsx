import React, { FC } from 'react'
import {
  BrowserRouter,
  Routes,
  Route,
} from 'react-router-dom'
import { IntlProvider } from 'react-intl'

import { useSelector } from 'react-redux'
import {
  useColorMode,
  Button,
} from '@chakra-ui/react'
import { ProtectedRouteProps } from './components/shared/ProtectedRoute'
import { fetchTranslations } from './store/translations'
import { fetchSettings } from './store/settings'
import { fetchUser } from './store/sessionAuth'
import LoginPage from './pages/login'
import RegisterPage from './pages/register'
import PasswordResetPage from './pages/password-reset'

import { useAppDispatch, RootState } from './store'


const App: FC = () => {
  const translations = useSelector((state: RootState) => state.translations)
  const settings = useSelector((state: RootState) => state.settings)
  const isLoggedIn = useSelector((state: RootState) => state.sessionAuth.isLoggedIn)
  const userFetched = useSelector((state: RootState) => state.sessionAuth.userFetched)
  const dispatch = useAppDispatch()

  if (Object.keys(translations).length === 0) dispatch(fetchTranslations())
  if (Object.keys(settings).length === 0) dispatch(fetchSettings())
  if (!userFetched) dispatch(fetchUser())

  const { colorMode, toggleColorMode } = useColorMode()

  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const routeProps: ProtectedRouteProps = {
    isAuthenticated: isLoggedIn,
    authPath: '/login',
    path: '/',
  }

  if (isLoggedIn) {
    window.location.replace('/dashboard/')
    return null
  }

  return (
    <IntlProvider
      locale={(Object.keys(translations).length !== 0 && translations.translations.locale) || 'en'}
      messages={(Object.keys(translations).length !== 0 && translations.translations.catalog) || {}}
      onError={(err) => {
        if (err.code === 'MISSING_TRANSLATION') {
          return
        }
        if (err.code === 'MISSING_DATA') {
          return
        }
        throw err
      }}
    >
      <BrowserRouter>
        <Button
          position="fixed"
          right="1rem"
          top="1rem"
          onClick={toggleColorMode}
        >
          Toggle
          {' '}
          {colorMode === 'light' ? 'Dark' : 'Light'}
        </Button>
        <Routes>
          <Route path="/" element={<LoginPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/password-reset" element={<PasswordResetPage />} />
        </Routes>
      </BrowserRouter>
    </IntlProvider>
  )
}

export default App
