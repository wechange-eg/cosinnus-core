import React from "react"
import {connect as reduxConnect} from "react-redux"
import {RouteComponentProps} from "react-router-dom"
import {withRouter} from "react-router"

import {RootState} from "../../stores/rootReducer"
import {fetchEvents} from "../../stores/events/effects"
import {DispatchedReduxThunkActionCreator} from "../../utils/types"
import {Event} from "../components/Event"
import {EventRoomState} from "../../stores/events/reducer"
import {Room} from "../../stores/room/models"

interface StageEventProps {
  id: number
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
  fetchEvents
}

function StageEventConnector (props: StageEventProps & RouteComponentProps) {
  const { id, events, fetchEvents, room } = props
  let event = null
  if (events && events.events) {
    event = events.events.find((e) => e.props.id === id)
  } else if (!events && !(events && events.loading)) {
    fetchEvents()
  }
  return <Event events={events} event={event} />
}

export const StageEvent = reduxConnect(mapStateToProps, mapDispatchToProps)(
  withRouter(StageEventConnector)
)
