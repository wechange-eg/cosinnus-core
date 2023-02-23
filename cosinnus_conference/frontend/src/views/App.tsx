import React, {Component} from "react"
import { ThemeProvider, StylesProvider, jssPreset } from "@material-ui/core/styles"
import { hot } from "react-hot-loader"
import { connect } from "react-redux"
import { HashRouter as Router, Switch } from "react-router-dom"
import {CssBaseline, Grid, Typography} from "@material-ui/core"
import {FormattedMessage, IntlProvider} from "react-intl"
import { create } from "jss"
import rtl from "jss-rtl"

// Configure JSS
const jss = create({ plugins: [...jssPreset().plugins, rtl()] });

import { RootState } from "../stores/rootReducer"
import { ProtectedRoute, ProtectedRouteProps } from "./routes/ProtectedRoute"
import { getTheme } from "../themes/themes"
import {
  fetchTranslations
} from "../stores/translations/effects"
import { TranslationsState } from "../stores/translations/reducer"
import {ThemeState} from "../stores/theme/reducer"
import {fetchUser} from "../stores/user/effects"
import {User} from "../stores/user/models"
import {DispatchedReduxThunkActionCreator} from "../utils/types"
import {Conference} from "../stores/conference/models"
import {fetchConference} from "../stores/conference/effects"
import {Nav} from "./components/Nav"
import {Lobby} from "./Lobby"
import {Stage} from "./Stage/list"
import {Discussions} from "./Discussions/list"
import {Workshops} from "./Workshops/list"
import {CoffeeTables} from "./CoffeeTables/list"
import {Organizations} from "./Organizations"
import {CoffeeTable} from "./CoffeeTables/detail"
import {Channels} from "./Channels/list"
import {Channel} from "./Channels/detail"
import {Workshop} from "./Workshops/detail"
import {Discussion} from "./Discussions/detail"
import {StageEvent} from "./Stage/detail"
import {Results} from "./Results"
import {Room} from "../stores/room/models"
import {Loading} from "./components/Loading"
import {Participant} from "../stores/participants/models"
import {Participants} from "./Participants/list"
import {Participant as ParticipantView} from "./Participants/detail"
import {Content} from "./components/Content/style"


interface AppProps {
  conference: Conference
  participants: Participant[]
  room: Room
  theme: ThemeState
  translations: TranslationsState
  user: User
  fetchConference: DispatchedReduxThunkActionCreator<Promise<void>>
  fetchParticipants: DispatchedReduxThunkActionCreator<Promise<void>>
  fetchUser: DispatchedReduxThunkActionCreator<Promise<void>>
  fetchTranslations: DispatchedReduxThunkActionCreator<Promise<void>>
}

function mapStateToProps(state: RootState) {
  return {
    conference: state.conference,
    theme: state.theme,
    room: state.room,
    translations: state.translations,
    user: state.user,
  }
}

const mapDispatchToProps = {
  fetchConference,
  fetchUser,
  fetchTranslations,
}


class AppConnector extends Component<AppProps> {
  constructor(props: AppProps) {
    super(props)
    const {translations, fetchTranslations} = props
    const {user, fetchUser} = props
    const {conference, fetchConference} = props

    if (!translations) fetchTranslations()
    if (!user) fetchUser()
    if (!conference) fetchConference()
  }

  getRoutes() {
    const { room, user } = this.props
    const routeProps: ProtectedRouteProps = {
      isAuthenticated: !!user,
      exact: true,
      path: "/",
    }
    return (room.props.type === "lobby" && (
      <Switch>
        <ProtectedRoute {...routeProps} component={Lobby} />
      </Switch>
      )) || (room.props.type === "stage" && (
      <Switch>
        <ProtectedRoute {...routeProps} component={Stage}/>
        <ProtectedRoute {...routeProps} path="/:id" render={props => (
          <StageEvent id={+props.match.params.id} {...props} />
        )}/>
      </Switch>
      )) || (room.props.type === "discussions" && (
      <Switch>
        <ProtectedRoute {...routeProps} component={Discussions}/>
        <ProtectedRoute {...routeProps} path="/:id" render={props => (
          <Discussion id={+props.match.params.id} {...props} />
        )}/>
      </Switch>
      )) || (room.props.type === "workshops" && (
      <Switch>
        <ProtectedRoute {...routeProps} component={Workshops}/>
        <ProtectedRoute {...routeProps} path="/:id" render={props => (
          <Workshop id={+props.match.params.id} {...props} />
        )}/>
      </Switch>
      )) || (room.props.type === "coffee_tables" && (
      <Switch>
        <ProtectedRoute {...routeProps} component={CoffeeTables}/>
        <ProtectedRoute {...routeProps} path="/:id" render={props => (
          <CoffeeTable id={+props.match.params.id} {...props} />
        )}/>
      </Switch>
      )) || (room.props.type === "networking" && (
      <Switch>
        <ProtectedRoute {...routeProps} component={Channels}/>
        <ProtectedRoute {...routeProps} path="/:id" render={props => (
          <Channel id={+props.match.params.id} {...props} />
        )}/>
      </Switch>
      )) || (room.props.type === "exhibition" && (
      <Switch>
        <ProtectedRoute {...routeProps} component={Organizations}/>
      </Switch>
    )) || (room.props.type === "results" && (
      <Switch>
        <ProtectedRoute {...routeProps} component={Results}/>
      </Switch>
    )) || (room.props.type === "participants" && (
      <Switch>
        <ProtectedRoute {...routeProps} component={Participants}/>
        <ProtectedRoute {...routeProps} path="/:id" render={props => (
          <ParticipantView id={+props.match.params.id} {...props} />
        )}/>
      </Switch>
    ))
  }

  render() {
    const { translations, conference, room } = this.props
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
          <ThemeProvider theme={getTheme(conference && conference.getThemeColor() || undefined)}>
            <StylesProvider jss={jss}>
              <CssBaseline/>
              <Nav/>
              {(room && this.getRoutes())
              || (window.conferenceRoomId && <Loading/>)
              || (
                <Grid container>
                  <Content>
                    <Typography component="h1">
                      <FormattedMessage id="Conference is being prepared"/>
                    </Typography>
                    <Typography component="p">
                      <FormattedMessage id="The conference is being prepared, please try again at a later date."/>
                    </Typography>
                  </Content>
                </Grid>
              )}
            </StylesProvider>
          </ThemeProvider>
        </Router>
      </IntlProvider>
    )
  }
}

export const App = hot(module)(
  connect(mapStateToProps, mapDispatchToProps)(AppConnector)
)
