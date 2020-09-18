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
import {useStyles as iframeUseStyles} from "../components/Iframe/style"
import {Content} from "../components/Content/style"
import {Sidebar} from "../components/Sidebar"
import {fetchEvents} from "../../stores/events/effects"
import {EventSlot} from "../../stores/events/models"
import {Channel} from "../components/Channel"
import {ManageRoomButtons} from "../components/ManageRoomButtons"

interface ChannelsProps {
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

function ChannelsConnector (props: ChannelsProps & RouteComponentProps) {
  const { events, fetchEvents, url } = props
  if (!events) {
    fetchEvents()
  }
  const iframeClasses = iframeUseStyles()
  return (
    <Grid container>
      <Content>
        <Typography component="h1">
          <FormattedMessage
            id="Connect with someone via videochat for 5 minutes"
            defaultMessage="Connect with someone via videochat for 5 minutes"
          />
        </Typography>
        {events && events.length > 0 && (
        <Grid container spacing={2}>
          {events.map((slot, index) => (
            slot.props.events.map((event, eventIndex) => (
            <Grid item key={index + "-" + eventIndex} sm={6} className="now">
              <Channel event={event} />
            </Grid>
            ))
          ))}
        </Grid>
        )
        || <Typography><FormattedMessage
          id="No networking channels."
          defaultMessage="No networking channels."
        /></Typography>
        }
        <ManageRoomButtons />
      </Content>
      {url && (
        <Sidebar elements={(
          <Iframe
            url={url}
            width="100%"
            height="100%"
            className={iframeClasses.sidebarIframe}
          />
        )} />
      )}
    </Grid>
  )
}

export const Channels = reduxConnect(mapStateToProps, mapDispatchToProps)(
  withRouter(ChannelsConnector)
)
