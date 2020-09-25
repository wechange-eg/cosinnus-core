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
import {ManageEventButtons} from "../components/ManageEventButtons"
import {Sidebar} from "../components/Sidebar"
import {IframeContent} from "../components/IframeContent"
import {EventRoomState} from "../../stores/events/reducer"

interface StageEventProps {
  id: number
  events: EventRoomState
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
  fetchEvents
}

function StageEventConnector (props: StageEventProps & RouteComponentProps) {
  const { id, events, fetchEvents, url } = props
  let event = null
  if (events && events.events) {
    event = events.events.find((e) => e.props.id === id)
  } else if (!events && !(events && events.loading)) {

    fetchEvents()
  }
  return (
    <Main container>
      {(event && (
        <Content className="fullheight">
          <Typography component="h1">{event.props.title}</Typography>
          {event.props.noteHtml && (
            <div className="description" dangerouslySetInnerHTML={{__html: event.props.noteHtml}} />
          )}
          <IframeContent url={event.props.url} />
          <ManageEventButtons event={event} />
        </Content>
      ))
      || <Content className="fullheight"><Loading /></Content>
      }
      {url && <Sidebar url={url} />}
    </Main>
  )
}

export const StageEvent = reduxConnect(mapStateToProps, mapDispatchToProps)(
  withRouter(StageEventConnector)
)
