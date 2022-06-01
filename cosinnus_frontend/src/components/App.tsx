import React, { Component } from "react"
import { Route } from "react-router"
import { BrowserRouter as Router, Switch } from "react-router-dom"
import { IntlProvider } from "react-intl"

import { ProtectedRoute, ProtectedRouteProps } from "./routes/ProtectedRoute"
import { ProfilePage } from "./Profile"
import { fetchTranslations } from "../reducers/translations"
import { fetchUser } from "../reducers/user"
import { LoginPage } from "./Login"
import { RegisterPage } from "./Register"

import { useAppDispatch, RootState } from "../rootStore"
import { useSelector } from 'react-redux'

export default function App() {
  const accessToken = useSelector((state: RootState) => state.auth.accessToken);
  const translations = useSelector((state: RootState) => state.translations);
  const user = useSelector((state: RootState) => state.user);
  const dispatch = useAppDispatch();

  if(!translations && !translations.locale) dispatch(fetchTranslations())
  if(!user && !user.username) dispatch(fetchUser())

  const routeProps: ProtectedRouteProps = {
    isAuthenticated: !!accessToken,
    authPath: "/login",
    exact: true,
    path: "/",
  }

  return (
    <IntlProvider
      locale={translations && translations.locale || "en"}
      messages={translations && translations.catalog || {}}
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
        <Switch>
          <Route exact path="/login"><LoginPage /></Route>
          <Route exact path="/register"><RegisterPage /></Route>
          <ProtectedRoute {...routeProps} component={ProfilePage} />
        </Switch>
      </Router>
    </IntlProvider>
  )
}