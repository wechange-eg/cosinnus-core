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
import {EventSlot} from "../../stores/events/models"
import {findEventById} from "../../utils/events"
import {ManageEventButtons} from "../components/ManageEventButtons"
import {IframeContent} from "../components/IframeContent"

interface ChannelProps {
  id: number
  events: EventSlot[]
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
  if (events) {
    event = findEventById(events, id)
  } else {
    fetchEvents()
  }
  return (
    <Main container>
      {event && (
        <Content>
          <Typography component="h1">{event.props.title}</Typography>
          {event.props.noteHtml && (
            <div className="description" dangerouslySetInnerHTML={{__html: event.props.noteHtml}} />
          )}
          <IframeContent url={event.props.url} />
          <ManageEventButtons event={event} />
        </Content>
      ) || (
        <Content>
          <Loading />
        </Content>
      )}
    </Main>
  )
}

export const Channel = reduxConnect(mapStateToProps, mapDispatchToProps)(
  withRouter(ChannelConnector)
)
