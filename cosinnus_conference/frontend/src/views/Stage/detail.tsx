import {
  Grid,
  Typography
} from "@material-ui/core"
import React, {useState} from "react"
import {connect as reduxConnect} from "react-redux"
import {RouteComponentProps} from "react-router-dom"
import {withRouter} from "react-router"

import {RootState} from "../../stores/rootReducer"
import {fetchEvents} from "../../stores/events/effects"
import {DispatchedReduxThunkActionCreator} from "../../utils/types"
import {Event} from "../../stores/events/models"
import {Content} from "../components/Content/style"
import {Main} from "../components/Main/style"
import {Loading} from "../components/Loading"
import {EventButtons} from "../components/EventButtons"
import {Sidebar} from "../components/Sidebar"
import {IframeContent} from "../components/IframeContent"
import {EventRoomState} from "../../stores/events/reducer"
import {FormattedMessage} from "react-intl"
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
  return (
    <Main container>
      {(event && (
        <Content className="fullheight detail-view">
          <Typography component="h1">{event.props.title}</Typography>
          {event.props.noteHtml && (
            <div className="description" dangerouslySetInnerHTML={{__html: event.props.noteHtml}} />
          )}
          <IframeContent url={event.props.url} html={event.props.rawHtml} />
          <EventButtons event={event} />
        </Content>
      ))
      || (events && events.loading) && (
        <Content className="fullheight"><Loading /></Content>
      ) || (
        <Content className="fullheight">
          <Typography><FormattedMessage id="Event not found."/></Typography>
        </Content>
      )}
      {room.props.showChat && room.props.url && <Sidebar url={room.props.url} />}
    </Main>
  )
}

export const StageEvent = reduxConnect(mapStateToProps, mapDispatchToProps)(
  withRouter(StageEventConnector)
)
