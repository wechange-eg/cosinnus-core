import {
  Typography
} from "@material-ui/core"
import React from "react"
import {connect as reduxConnect} from "react-redux"
import {RouteComponentProps} from "react-router-dom"
import {withRouter} from "react-router"

import {RootState} from "../../stores/rootReducer"
import {DispatchedReduxThunkActionCreator} from "../../utils/types"
import {Event} from "../../stores/events/models"
import {Content} from "../components/Content/style"
import {useStyles} from "./style"
import {Loading} from "../components/Loading"
import {Main} from "../components/Main/style"
import {fetchEvents} from "../../stores/events/effects"
import {ManageEventButtons} from "../components/ManageEventButtons"
import {IframeContent} from "../components/IframeContent"
import {EventRoomState} from "../../stores/events/reducer"

interface CoffeeTableProps {
  id: number
  events: EventRoomState
  fetchEvents: DispatchedReduxThunkActionCreator<Promise<void>>
}

function mapStateToProps(state: RootState, _ownProps: CoffeeTableProps) {
  return {
    events: state.events[state.room.props.id]
  }
}

const mapDispatchToProps = {
  fetchEvents: fetchEvents
}

function CoffeeTableConnector (props: CoffeeTableProps & RouteComponentProps) {
  const { id, events, fetchEvents } = props
  let event = null
  if (events && events.events) {
    event = events.events.find((e) => e.props.id === id)
  } else if (!(events && events.loading)) {
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
    </Main>
  )
}

export const CoffeeTable = reduxConnect(mapStateToProps, mapDispatchToProps)(
  withRouter(CoffeeTableConnector)
)
