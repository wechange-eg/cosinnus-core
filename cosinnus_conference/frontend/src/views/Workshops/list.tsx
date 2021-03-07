import {
  Grid,
  Typography
} from "@material-ui/core"
import React, {useEffect, useState} from "react"
import {connect as reduxConnect} from "react-redux"
import {RouteComponentProps} from "react-router-dom"
import {withRouter} from "react-router"
import {FormattedMessage} from "react-intl"

import {RootState} from "../../stores/rootReducer"
import {DispatchedReduxThunkActionCreator} from "../../utils/types"
import {Content} from "../components/Content/style"
import {Sidebar} from "../components/Sidebar"
import {fetchEvents} from "../../stores/events/effects"
import {ManageRoomButtons} from "../components/ManageRoomButtons"
import {Room} from "../../stores/room/models"
import {EventGrid} from "../components/EventGrid"
import {EventRoomState} from "../../stores/events/reducer"
import {Loading} from "../components/Loading"
import {EventParticipantsRoomState} from "../../stores/eventParticipants/reducer"
import {fetchEventParticipants} from "../../stores/eventParticipants/effects"
import {Notification} from "../components/Notification"

interface WorkshopsProps {
  events: EventRoomState
  eventParticipants: EventParticipantsRoomState
  fetchEvents: DispatchedReduxThunkActionCreator<Promise<void>>
  fetchEventParticipants: DispatchedReduxThunkActionCreator<Promise<void>>
  room: Room
}

function mapStateToProps(state: RootState) {
  return {
    events: state.events[state.room.props.id],
    eventParticipants: state.eventParticipants[state.room.props.id],
    room: state.room,
  }
}

const mapDispatchToProps = {
  fetchEvents,
  fetchEventParticipants
}

function WorkshopsConnector (props: WorkshopsProps & RouteComponentProps) {
  const { events, eventParticipants, fetchEvents, fetchEventParticipants, room } = props
  // Rerender every minute
  const [time, setTime] = useState(new Date())
  useEffect(() => {
    const intervalId = setInterval(() => setTime(new Date()), 60000)
    return () => clearInterval(intervalId)
  }, [])

  if (!events && !(events && events.loading)) fetchEvents()
  if (!eventParticipants && !(eventParticipants && eventParticipants.loading)) fetchEventParticipants()

  return (
    <Grid container>
      <Content>
        <Notification />
        <Typography component="h1"><FormattedMessage id="Agenda" /></Typography>
        {room.props.descriptionHtml && (
          <div className="description" dangerouslySetInnerHTML={{__html: room.props.descriptionHtml}} />
        )}
        {(events && events.events && events.events.length > 0 && (
          <EventGrid events={events.events} eventParticipants={eventParticipants && eventParticipants.participants} />)
        ) || (events && events.loading && <Loading />)
        || <Typography><FormattedMessage id="No workshops." /></Typography>
        }
        <ManageRoomButtons />
      </Content>
      {room.props.showChat && room.props.url && <Sidebar url={room.props.url} />}
    </Grid>
  )
}

export const Workshops = reduxConnect(mapStateToProps, mapDispatchToProps)(
  withRouter(WorkshopsConnector)
)
