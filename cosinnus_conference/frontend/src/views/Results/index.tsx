import {
  Grid,
  Typography
} from "@material-ui/core"
import React from "react"
import {connect as reduxConnect} from "react-redux"
import {RouteComponentProps} from "react-router-dom"
import {withRouter} from "react-router"
import {FormattedMessage} from "react-intl";
import Iframe from "react-iframe"

import {RootState} from "../../stores/rootReducer"
import {DispatchedReduxThunkActionCreator} from "../../utils/types"
import {EventSlot} from "../../stores/events/models"
import {useStyles as iframeUseStyles} from "../components/Iframe/style"
import {Content} from "../components/Content/style"
import {Sidebar} from "../components/Sidebar"
import {fetchWorkshops} from "../../stores/workshops/effects"
import {useStyles} from "./style"
import {EventCard} from "../components/EventCard"
import {Main} from "../components/Main/style"
import {Loading} from "../components/Loading"
import {fetchEvents} from "../../stores/events/effects"
import {findEventById} from "../../utils/events"

interface ResultsProps {
  url: string
}

function mapStateToProps(state: RootState, _ownProps: ResultsProps) {
  return {
    url: state.conference && state.conference.rooms[window.conferenceRoomSlug].url,
  }
}

const mapDispatchToProps = {
}

function ResultsConnector (props: ResultsProps & RouteComponentProps) {
  const { url } = props
  const iframeClasses = iframeUseStyles()
  return (
    <Main container>
      {url && (
        <Content>
          <Typography component="h1">
            <FormattedMessage id="Results" defaultMessage="Results" />
          </Typography>
          <div className={iframeClasses.resultsIframe}>
            <Iframe
              url={url}
              width="100%"
              height="100%"
            />
          </div>
        </Content>
      ) || (
        <Content>
          <Loading />
        </Content>
      )}
    </Main>
  )
}

export const Results = reduxConnect(mapStateToProps, mapDispatchToProps)(
  withRouter(ResultsConnector)
)
