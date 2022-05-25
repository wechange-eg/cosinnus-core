import React, {Component} from "react"
import { connect } from "react-redux"
import { Route } from "react-router"
import { BrowserRouter as Router, Switch } from "react-router-dom"
import { IntlProvider} from "react-intl"

import { ProtectedRoute, ProtectedRouteProps } from "./routes/ProtectedRoute"
import {
  fetchTranslations
} from "../stores/translations/effects"
import { TranslationsState } from "../stores/translations/reducer"
import {fetchUser} from "../stores/user/effects"
import {User} from "../stores/user/models"
import {DispatchedReduxThunkActionCreator} from "../utils/types"
import {Map} from "./Map"
import {Settings} from "../stores/settings/models"
import {fetchSettings} from "../stores/settings/effects"
import {Login} from "./Login"
import {Register} from "./Register"

interface AppProps {
  isLoggedIn: boolean
  authToken: string
  settings: Settings
  user: User
  translations: TranslationsState
  fetchSettings: DispatchedReduxThunkActionCreator<Promise<void>>
  fetchTranslations: DispatchedReduxThunkActionCreator<Promise<void>>
  fetchUser: DispatchedReduxThunkActionCreator<Promise<void>>
}

function mapStateToProps(state: any) {
  return {
    isLoggedIn: state.auth.isLoggedIn,
    user: state.user
  }
}

const mapDispatchToProps = {
  fetchSettings,
  fetchUser,
  fetchTranslations,
}

class AppConnector extends Component<AppProps> {

  render() {
    const {settings, fetchSettings} = this.props
    const {isLoggedIn} = this.props
    const {translations, fetchTranslations} = this.props
    if (!settings) fetchSettings()
    if (!translations) fetchTranslations()
    if (isLoggedIn) fetchUser()

    const routeProps: ProtectedRouteProps = {
      isAuthenticated: !!isLoggedIn,
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
            // console.warn("Missing translation", err.message);
            return;
          }
          if (err.code === "MISSING_DATA") {
            // console.warn("Missing data", err.message);
            return;
          }
          throw err;
        }}
      >
        <Router>
          <Switch>
            <Route exact path="/login"><Login /></Route>
            <Route exact path="/register"><Register /></Route>
            <ProtectedRoute {...routeProps} component={Map}/>
          </Switch>
        </Router>
      </IntlProvider>
    )
  }
}

export const App = connect(mapStateToProps, mapDispatchToProps)(AppConnector)
