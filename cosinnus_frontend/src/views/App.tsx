import React, {Component} from "react"
import { ThemeProvider } from "@material-ui/core/styles"
import { hot } from "react-hot-loader"
import { connect } from "react-redux"
import { Route } from "react-router"
import { HashRouter as Router, Switch } from "react-router-dom"
import {CssBaseline} from "@material-ui/core"
import {FormattedMessage, IntlProvider} from "react-intl"

import { RootState } from "../stores/rootReducer"
import { ProtectedRoute, ProtectedRouteProps } from "./routes/ProtectedRoute"
import { getTheme } from "../themes/themes"
import {
  fetchTranslations
} from "../stores/translations/effects"
import { TranslationsState } from "../stores/translations/reducer"
import {fetchUser} from "../stores/user/effects"
import {User} from "../stores/user/models"
import {DispatchedReduxThunkActionCreator} from "../utils/types"
import {NavBar} from "./components/NavBar"
import {Search} from "./Search"
import {Result} from "./Result"
import {Map} from "./Map"
import {Settings} from "../stores/settings/models"
import {fetchSettings} from "../stores/settings/effects"
import {Login} from "./components/Login";

interface AppProps {
  authToken: string
  settings: Settings
  user: User
  translations: TranslationsState
  fetchSettings: DispatchedReduxThunkActionCreator<Promise<void>>
  fetchTranslations: DispatchedReduxThunkActionCreator<Promise<void>>
  fetchUser: DispatchedReduxThunkActionCreator<Promise<void>>
}

function mapStateToProps(state: RootState) {
  return {
    authToken: state.auth.token,
    settings: state.settings,
    translations: state.translations,
  }
}

const mapDispatchToProps = {
  fetchSettings,
  fetchUser,
  fetchTranslations,
}

class AppConnector extends Component<AppProps> {
  render() {
    const {authToken} = this.props
    const {settings, fetchSettings} = this.props
    const {user, fetchUser} = this.props
    const {translations, fetchTranslations} = this.props
    if (!settings) fetchSettings()
    if (!translations) fetchTranslations()
    if (authToken) {
      if (!user) fetchUser()
    }

    const routeProps: ProtectedRouteProps = {
      isAuthenticated: !!authToken,
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
          <ThemeProvider theme={getTheme(settings && settings.getThemeColor() || undefined)}>
            <CssBaseline/>
            <NavBar />
            <Switch>
              <Route exact path="/login"><Login /></Route>
              <ProtectedRoute {...routeProps} component={Map}/>
              <ProtectedRoute {...routeProps} path="/search/" component={Search}/>
              <ProtectedRoute {...routeProps} path="/r/:id" render={props => (
                <Result id={+props.match.params.id} {...props} />
              )}/>
            </Switch>
          </ThemeProvider>
        </Router>
      </IntlProvider>
    )
  }
}

export const App = hot(module)(
  connect(mapStateToProps, mapDispatchToProps)(AppConnector)
)
