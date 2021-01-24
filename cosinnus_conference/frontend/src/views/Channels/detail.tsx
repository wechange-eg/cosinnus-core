import React from "react"
import {connect as reduxConnect} from "react-redux"
import {RouteComponentProps} from "react-router-dom"
import {withRouter} from "react-router"

import {RootState} from "../../stores/rootReducer"
import {DispatchedReduxThunkActionCreator} from "../../utils/types"
import {fetchEvents} from "../../stores/events/effects"
import {Event} from "../components/Event"
import {EventRoomState} from "../../stores/events/reducer"

interface ChannelProps {
  id: number
  events: EventRoomState
  fetchEvents: DispatchedReduxThunkActionCreator<Promise<void>>
}

function mapStateToProps(state: RootState) {
  return {
    events: state.events[state.room.props.id],
  }
}

const mapDispatchToProps = {
  fetchEvents
}

function ChannelConnector (props: ChannelProps & RouteComponentProps) {
  const { id, events, fetchEvents } = props
  let event = null
  if (events && events.events) {
    event = events.events.find((e) => e.props.id === id)
  } else if (!events && !(events && events.loading)) {
    fetchEvents()
  }
  return <Event events={events} event={event} />
}

export const Channel = reduxConnect(mapStateToProps, mapDispatchToProps)(
  withRouter(ChannelConnector)
)
