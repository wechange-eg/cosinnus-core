import React, { useRef } from "react"
import { ThemeProvider } from "@material-ui/core/styles"
import { hot } from "react-hot-loader"
import { connect } from "react-redux"
import { HashRouter as Router, Switch } from "react-router-dom"
import { CssBaseline } from "@material-ui/core"
import { IntlProvider } from "react-intl"

import { RootState } from "../stores/rootReducer"
import { ProtectedRoute, ProtectedRouteProps } from "./routes/ProtectedRoute"
import { theme } from "../themes/themes"
import {
  fetchTranslations
} from "../stores/translations/effects"
import { TranslationsState } from "../stores/translations/reducer"
import {ThemeState} from "../stores/theme/reducer"
import {fetchUser} from "../stores/user/effects"
import {User} from "../stores/user/models"
import {DispatchedReduxThunkActionCreator} from "../utils/types"
import {ConferenceState} from "../stores/conference/reducer"
import {fetchConference} from "../stores/conference/effects"
import {Nav} from "./components/Nav"
import {Lobby} from "./Lobby"
import {Stage} from "./Stage"
import {Discussions} from "./Discussions"
import {Workshops} from "./Workshops"
import {CoffeeTables} from "./CoffeeTables"
import {Networking} from "./Networking"
import {Organisations} from "./Organisations"

interface AppProps {
  conference: ConferenceState
  theme: ThemeState
  translations: TranslationsState
  user: User

  fetchConference: DispatchedReduxThunkActionCreator<Promise<void>>
  fetchUser: DispatchedReduxThunkActionCreator<Promise<void>>
  fetchTranslations: DispatchedReduxThunkActionCreator<Promise<void>>
}

function mapStateToProps(state: RootState) {
  return {
    conference: state.conference,
    theme: state.theme,
    translations: state.translations,
    user: state.user,
  }
}

const mapDispatchToProps = {
  fetchConference,
  fetchUser,
  fetchTranslations,
}

function AppConnector(props: AppProps) {
  const { translations, fetchTranslations } = props
  const { user, fetchUser } = props
  const { conference, fetchConference } = props

  if (!translations) {
    fetchTranslations()
  }

  if (!user) {
    fetchUser()
  }

  if (!conference) {
    fetchConference()
  }

  const protRouteProps: ProtectedRouteProps = {
    isAuthenticated: !!user
  }

  const view = window.conferenceView;
  return (
    <IntlProvider
      locale={translations && translations.locale || "en"}
      messages={translations && translations.catalog || {}}
    >
      <Router>
        <ThemeProvider theme={theme}>
          <CssBaseline />
          <Nav />
          <Switch>
            {(view === "lobby" &&
              <ProtectedRoute {...protRouteProps} exact path="/" component={Lobby}/>)
              || (view === "stage" &&
              <ProtectedRoute {...protRouteProps} exact path="/" component={Stage}/>)
              || (view === "discussions" &&
              <ProtectedRoute {...protRouteProps} exact path="/" component={Discussions}/>)
              || (view === "workshops" &&
              <ProtectedRoute {...protRouteProps} exact path="/" component={Workshops}/>)
              || (view === "coffee-tables" &&
              <ProtectedRoute {...protRouteProps} exact path="/" component={CoffeeTables}/>)
              || (view === "networking" &&
              <ProtectedRoute {...protRouteProps} exact path="/" component={Networking}/>)
              || (view === "exhibition" &&
              <ProtectedRoute {...protRouteProps} exact path="/" component={Organisations}/>)
            }
          </Switch>
        </ThemeProvider>
      </Router>
    </IntlProvider>
  )
}

export const App = hot(module)(
  connect(mapStateToProps, mapDispatchToProps)(AppConnector)
)
