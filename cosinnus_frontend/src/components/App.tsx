import React, { Component } from "react"
import { Route } from "react-router"
import { BrowserRouter as Router, Switch } from "react-router-dom"
import { IntlProvider } from "react-intl"

import { ProtectedRoute, ProtectedRouteProps } from "./routes/ProtectedRoute"
import { ProfilePage } from "./Profile"
import { fetchTranslations } from "../store/translations"
import { fetchSettings } from "../store/settings"
import { fetchUser } from "../store/user"
import { LoginPage } from "./Login"
import { RegisterPage } from "./Register"

import { useAppDispatch, RootState } from "../store"
import { useSelector } from 'react-redux'

import {
  Container,
  useColorMode,
  Button,
  Heading,
  Text,
  Divider,
} from "@chakra-ui/react"


export default function App() {
  const accessToken = useSelector((state: RootState) => state.auth.accessToken);
  const translations = useSelector((state: RootState) => state.translations);
  const settings = useSelector((state: RootState) => state.settings);
  const profile = useSelector((state: RootState) => state.profile);
  const dispatch = useAppDispatch();

  if(Object.keys(translations).length === 0) dispatch(fetchTranslations())
  if(Object.keys(settings).length === 0) dispatch(fetchSettings())
  if(accessToken && Object.keys(profile).length === 0) dispatch(fetchUser())

  const { colorMode, toggleColorMode } = useColorMode()

  const routeProps: ProtectedRouteProps = {
    isAuthenticated: !!accessToken,
    authPath: "/login",
    exact: true,
    path: "/",
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
          <Route exact path="/login"><LoginPage /></Route>
          <Route exact path="/register"><RegisterPage /></Route>
          <ProtectedRoute {...routeProps} component={ProfilePage} />
        </Switch>
      </Router>
    </IntlProvider>
  )
}