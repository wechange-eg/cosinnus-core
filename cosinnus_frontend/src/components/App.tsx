import React, { Component } from "react"
import { Route } from "react-router"
import { BrowserRouter as Router, Switch } from "react-router-dom"
import { IntlProvider } from "react-intl"

import { ProtectedRoute, ProtectedRouteProps } from "./routes/ProtectedRoute"
import { fetchTranslations } from "../store/translations"
import { fetchSettings } from "../store/settings"
import { fetchUser } from "../store/sessionAuth"
import { LoginPage } from "./auth/Login"
import { RegisterPage } from "./auth/Register"
import { PasswordResetPage } from "./auth/PasswordReset"

import { useAppDispatch, RootState } from "../store"
import { useSelector } from 'react-redux'

import {
  useColorMode,
  Button
} from "@chakra-ui/react"


export default function App() {
  const translations = useSelector((state: RootState) => state.translations);
  const settings = useSelector((state: RootState) => state.settings);
  const isLoggedIn = useSelector((state: RootState) => state.sessionAuth.isLoggedIn);
  const userFetched = useSelector((state: RootState) => state.sessionAuth.userFetched);
  const dispatch = useAppDispatch();

  if (Object.keys(translations).length === 0) dispatch(fetchTranslations())
  if (Object.keys(settings).length === 0) dispatch(fetchSettings())
  if(! userFetched) dispatch(fetchUser())

  const { colorMode, toggleColorMode } = useColorMode()

  const routeProps: ProtectedRouteProps = {
    isAuthenticated: isLoggedIn,
    authPath: "/login",
    exact: true,
    path: "/",
  }

  if (isLoggedIn) {
    window.location.replace("/dashboard/");
    return null;
  }

  return (
    <IntlProvider
      locale={Object.keys(translations).length !== 0 && translations.translations.locale || "en"}
      messages={Object.keys(translations).length !== 0 && translations.translations.catalog || {}}
      onError={(err) => {
        if (err.code === "MISSING_TRANSLATION") {
          return;
        }
        if (err.code === "MISSING_DATA") {
          return;
        }
        throw err;
      }}
    >
      <Router>
        <Button
          position="fixed"
          right="1rem"
          top="1rem"
          onClick={toggleColorMode}
        >
          Toggle {colorMode === "light" ? "Dark" : "Light"}
        </Button>
        <Switch>
          <Route exact path="/"><LoginPage /></Route>
          <Route exact path="/login"><LoginPage /></Route>
          <Route exact path="/register"><RegisterPage /></Route>
          <Route exact path="/password-reset"><PasswordResetPage /></Route>
        </Switch>
      </Router>
    </IntlProvider>
  )
}