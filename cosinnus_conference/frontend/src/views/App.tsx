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
import {Stage} from "./Stage/list"
import {Discussions} from "./Discussions/list"
import {Workshops} from "./Workshops/list"
import {CoffeeTables} from "./CoffeeTables/list"
import {Networking} from "./Networking/list"
import {Organisations} from "./Organisations"
import {CoffeeTable} from "./CoffeeTables/detail"
import {Channels} from "./Channels/list"
import {Channel} from "./Channels/detail"
import {Workshop} from "./Workshops/detail"
import {Discussion} from "./Discussions/detail"
import {StageEvent} from "./Stage/detail"
import {Results} from "./Results"

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

  function getRoutes(room: string) {
    const routeProps: ProtectedRouteProps = {
      isAuthenticated: !!user,
      exact: true,
      path: "/",
    }
    return (room === "lobby" && (
      <Switch>
        <ProtectedRoute {...routeProps} component={Lobby} />
      </Switch>
      )) || (room === "stage" && (
      <Switch>
        <ProtectedRoute {...routeProps} component={Stage}/>
        <ProtectedRoute {...routeProps} path="/:id" render={props => (
          <StageEvent id={+props.match.params.id} {...props} />
        )}/>
      </Switch>
      )) || (room === "discussions" && (
      <Switch>
        <ProtectedRoute {...routeProps} component={Discussions}/>
        <ProtectedRoute {...routeProps} path="/:id" render={props => (
          <Discussion id={+props.match.params.id} {...props} />
        )}/>
      </Switch>
      )) || (room === "workshops" && (
      <Switch>
        <ProtectedRoute {...routeProps} component={Workshops}/>
        <ProtectedRoute {...routeProps} path="/:id" render={props => (
          <Workshop id={+props.match.params.id} {...props} />
        )}/>
      </Switch>
      )) || (room === "coffee-tables" && (
      <Switch>
        <ProtectedRoute {...routeProps} component={CoffeeTables}/>
        <ProtectedRoute {...routeProps} path="/:id" render={props => (
          <CoffeeTable id={+props.match.params.id} {...props} />
        )}/>
      </Switch>
      )) || (room === "networking" && (
      <Switch>
        <ProtectedRoute {...routeProps} component={Channels}/>
        <ProtectedRoute {...routeProps} path="/:id" render={props => (
          <Channel id={+props.match.params.id} {...props} />
        )}/>
      </Switch>
      )) || (room === "exhibition" && (
      <Switch>
        <ProtectedRoute {...routeProps} component={Organisations}/>
      </Switch>
    )) || (room === "results" && (
      <Switch>
        <ProtectedRoute {...routeProps} component={Results}/>
      </Switch>
    ))
  }

  const room = window.conferenceRoom
  return (
    <IntlProvider
      locale={translations && translations.locale || "en"}
      messages={translations && translations.catalog || {}}
    >
      <Router>
        <ThemeProvider theme={theme}>
          <CssBaseline />
          <Nav />
          {getRoutes(room)}
        </ThemeProvider>
      </Router>
    </IntlProvider>
  )
}

export const App = hot(module)(
  connect(mapStateToProps, mapDispatchToProps)(AppConnector)
)
