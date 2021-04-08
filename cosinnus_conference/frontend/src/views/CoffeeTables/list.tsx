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
import {useStyles} from "./style"
import {CoffeeTable} from "../components/CoffeeTable"
import {fetchEvents} from "../../stores/events/effects"
import {ManageRoomButtons} from "../components/ManageRoomButtons"
import {Room} from "../../stores/room/models"
import {Event} from "../../stores/event/models"
import {Loading} from "../components/Loading"
import {EventRoomState} from "../../stores/events/reducer"
import {EventParticipantsRoomState} from "../../stores/eventParticipants/reducer"
import {fetchEventParticipants} from "../../stores/eventParticipants/effects"
import {Notification} from "../components/Notification"

interface CoffeeTablesProps {
  events: EventRoomState
  eventParticipants: EventParticipantsRoomState
  fetchEvents: DispatchedReduxThunkActionCreator<Promise<void>>
  fetchEventParticipants: DispatchedReduxThunkActionCreator<Promise<void>>
  room: Room
}

function mapStateToProps(state: RootState, _ownProps: CoffeeTablesProps) {
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

function CoffeeTablesConnector (props: CoffeeTablesProps & RouteComponentProps) {
  const { events, eventParticipants, fetchEvents, fetchEventParticipants, room } = props
  // Rerender every minute
  const [time, setTime] = useState(new Date())
  useEffect(() => {
    const intervalId = setInterval(() => setTime(new Date()), 60000)
    return () => clearInterval(intervalId)
  }, [])

  if (!events && !(events && events.loading)) fetchEvents()
  if (!eventParticipants && !(eventParticipants && eventParticipants.loading)) fetchEventParticipants()

  function getEventParticipantCount(event: Event) {
    return eventParticipants && eventParticipants.participants && eventParticipants.participants[event.props.id]
  }
  const classes = useStyles()
  return (
    <Grid container>
      <Content>
        <Notification />
        <div className={classes.section}>
          <Typography component="h1"><FormattedMessage id="Happening now" /></Typography>
          {room.props.descriptionHtml && (
            <div className="description" dangerouslySetInnerHTML={{__html: room.props.descriptionHtml}} />
          )}
          {(events && events.events && events.events.length > 0 && (
            <Grid container spacing={4}>
              {events.events.map((event, index) => (
                <Grid item key={index} sm={6} className="now">
                  <CoffeeTable event={event} participantsCount={getEventParticipantCount(event)} />
                </Grid>
              ))}
            </Grid>
          ))
          || (events && events.loading && <Loading />)
          || <Typography><FormattedMessage id="No coffee tables." /></Typography>
        }
        </div>
        <ManageRoomButtons />
      </Content>
      {room.props.showChat && room.props.url && <Sidebar url={room.props.url} />}
    </Grid>
  )
}

export const CoffeeTables = reduxConnect(mapStateToProps, mapDispatchToProps)(
  withRouter(CoffeeTablesConnector)
)
