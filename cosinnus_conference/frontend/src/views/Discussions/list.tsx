import {
  Grid, ListItem, ListItemText,
  Typography
} from "@material-ui/core"
import React from "react"
import {connect as reduxConnect} from "react-redux"
import {RouteComponentProps} from "react-router-dom"
import {withRouter, useHistory} from "react-router"
import {FormattedMessage} from "react-intl";
import Iframe from "react-iframe"
import clsx from "clsx"

import {RootState} from "../../stores/rootReducer"
import {DispatchedReduxThunkActionCreator} from "../../utils/types"
import {EventSlot} from "../../stores/events/models"
import {useStyles as iframeUseStyles} from "../components/Iframe/style"
import {formatTime} from "../../utils/events"
import {Content} from "../components/Content/style"
import {EventList} from "../components/EventList"
import {Sidebar} from "../components/Sidebar"
import {fetchEvents} from "../../stores/events/effects"
import {ManageRoomButtons} from "../components/ManageRoomButtons"

interface DiscussionsProps {
  events: EventSlot[]
  fetchEvents: DispatchedReduxThunkActionCreator<Promise<void>>
  url: string
}

function mapStateToProps(state: RootState) {
  return {
    events: state.events[state.room.props.id],
    url: state.room.props.url,
  }
}

const mapDispatchToProps = {
  fetchEvents: fetchEvents
}

function DiscussionsConnector (props: DiscussionsProps & RouteComponentProps) {
  const { events, fetchEvents, url } = props
  if (!events) {
    fetchEvents()
  }
  const iframeClasses = iframeUseStyles()
  return (
    <Grid container>
      <Content>
        <Typography component="h1"><FormattedMessage id="Agenda" defaultMessage="Agenda" /></Typography>
        <EventList events={events} />
        <ManageRoomButtons />
      </Content>
      {url && (
        <Sidebar elements={(
          <Iframe
            url={url}
            width="100%"
            height="100%"
            className={iframeClasses.sidebarIframe}
            allow="microphone *; camera *"
          />
        )} />
      )}
    </Grid>
  )
}

export const Discussions = reduxConnect(mapStateToProps, mapDispatchToProps)(
  withRouter(DiscussionsConnector)
)
