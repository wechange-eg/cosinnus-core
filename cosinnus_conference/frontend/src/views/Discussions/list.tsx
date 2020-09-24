import {
  Grid, ListItem, ListItemText,
  Typography
} from "@material-ui/core"
import React, {useEffect, useState} from "react"
import {connect as reduxConnect} from "react-redux"
import {RouteComponentProps} from "react-router-dom"
import {withRouter} from "react-router"
import {FormattedMessage} from "react-intl";
import Iframe from "react-iframe"

import {RootState} from "../../stores/rootReducer"
import {DispatchedReduxThunkActionCreator} from "../../utils/types"
import {EventSlot} from "../../stores/events/models"
import {Content} from "../components/Content/style"
import {EventList} from "../components/EventList"
import {Sidebar} from "../components/Sidebar"
import {fetchEvents} from "../../stores/events/effects"
import {ManageRoomButtons} from "../components/ManageRoomButtons"
import {Room} from "../../stores/room/models"

interface DiscussionsProps {
  events: EventSlot[]
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

function DiscussionsConnector (props: DiscussionsProps & RouteComponentProps) {
  const { events, fetchEvents, room } = props
  // Rerender every minute
  const [time, setTime] = useState(new Date())
  useEffect(() => { setInterval(() => setTime(new Date()), 60000) })

  if (!events) {
    fetchEvents()
  }
  return (
    <Grid container>
      <Content>
        <Typography component="h1"><FormattedMessage id="Agenda" /></Typography>
        {room.props.descriptionHtml && (
          <div className="description" dangerouslySetInnerHTML={{__html: room.props.descriptionHtml}} />
        )}
        <EventList events={events} />
        <ManageRoomButtons />
      </Content>
      {room.props.url && <Sidebar url={room.props.url} />}
    </Grid>
  )
}

export const Discussions = reduxConnect(mapStateToProps, mapDispatchToProps)(
  withRouter(DiscussionsConnector)
)
