import {
  Grid,
  Typography
} from "@material-ui/core"
import React, {useEffect, useState} from "react"
import {connect as reduxConnect} from "react-redux"
import {RouteComponentProps} from "react-router-dom"
import {withRouter} from "react-router"
import {FormattedMessage} from "react-intl";

import {RootState} from "../../stores/rootReducer"
import {DispatchedReduxThunkActionCreator} from "../../utils/types"
import {Content} from "../components/Content/style"
import {Sidebar} from "../components/Sidebar"
import {fetchEvents} from "../../stores/events/effects"
import {Event} from "../../stores/events/models"
import {Channel} from "../components/Channel"
import {ManageRoomButtons} from "../components/ManageRoomButtons"
import {Room} from "../../stores/room/models"
import {EventRoomState} from "../../stores/events/reducer"
import {Loading} from "../components/Loading"

interface ChannelsProps {
  events: EventRoomState
  fetchEvents: DispatchedReduxThunkActionCreator<Promise<void>>
  room: Room
}

function mapStateToProps(state: RootState) {
  return {
    events: state.events[state.room.props.id],
    room: state.room,
  }
}

const mapDispatchToProps = {
  fetchEvents: fetchEvents
}

function ChannelsConnector (props: ChannelsProps & RouteComponentProps) {
  const { events, fetchEvents, room } = props
  // Rerender every minute
  const [time, setTime] = useState(new Date())
  useEffect(() => {
    const intervalId = setInterval(() => setTime(new Date()), 60000)
    return () => clearInterval(intervalId)
  }, [])

  if (!events && !(events && events.loading)) fetchEvents()

  return (
    <Grid container>
      <Content>
        <Typography component="h1">
          <FormattedMessage id="Connect with someone via videochat for 5 minutes" />
        </Typography>
        {room.props.descriptionHtml && (
          <div className="description" dangerouslySetInnerHTML={{__html: room.props.descriptionHtml}} />
        )}
        {(events && events.events && events.events.length > 0 && (
        <Grid container spacing={2}>
          {events.events.map((event, index) => (
            <Grid item key={index} sm={6} className="now">
              <Channel event={event} />
            </Grid>
          ))}
        </Grid>
        ))
        || (events && events.loading && <Loading />)
        || <Typography><FormattedMessage id="No networking channels." /></Typography>
        }
        <ManageRoomButtons />
      </Content>
      {room.props.showChat && room.props.url && <Sidebar url={room.props.url} />}
    </Grid>
  )
}

export const Channels = reduxConnect(mapStateToProps, mapDispatchToProps)(
  withRouter(ChannelsConnector)
)
