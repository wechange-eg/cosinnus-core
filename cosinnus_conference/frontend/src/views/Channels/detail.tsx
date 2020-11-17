import {
  Typography
} from "@material-ui/core"
import React from "react"
import {connect as reduxConnect} from "react-redux"
import {RouteComponentProps} from "react-router-dom"
import {withRouter} from "react-router"

import {RootState} from "../../stores/rootReducer"
import {DispatchedReduxThunkActionCreator} from "../../utils/types"
import {Content} from "../components/Content/style"
import {Main} from "../components/Main/style"
import {Loading} from "../components/Loading"
import {fetchEvents} from "../../stores/events/effects"
import {Event} from "../../stores/events/models"
import {EventButtons} from "../components/EventButtons"
import {IframeContent} from "../components/IframeContent"
import {EventRoomState} from "../../stores/events/reducer"
import {FormattedMessage} from "react-intl"

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
  return (
    <Main container>
      {(events && events.events && events.events.length > 0 && (
        <Content className="fullheight">
          <Typography component="h1">{event.props.title}</Typography>
          {event.props.noteHtml && (
            <div className="description" dangerouslySetInnerHTML={{__html: event.props.noteHtml}} />
          )}
          <IframeContent url={event.props.url} />
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
    </Main>
  )
}

export const Channel = reduxConnect(mapStateToProps, mapDispatchToProps)(
  withRouter(ChannelConnector)
)
