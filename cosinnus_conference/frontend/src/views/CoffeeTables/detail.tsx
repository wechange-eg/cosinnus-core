import {
  Typography
} from "@material-ui/core"
import React from "react"
import {connect as reduxConnect} from "react-redux"
import {RouteComponentProps} from "react-router-dom"
import {withRouter} from "react-router"

import {RootState} from "../../stores/rootReducer"
import {DispatchedReduxThunkActionCreator} from "../../utils/types"
import {EventSlot} from "../../stores/events/models"
import {useStyles as iframeUseStyles} from "../components/Iframe/style"
import {Content} from "../components/Content/style"
import {useStyles} from "./style"
import {Loading} from "../components/Loading"
import {Main} from "../components/Main/style"
import {fetchEvents} from "../../stores/events/effects"
import {findEventById} from "../../utils/events"
import {Room} from "../../stores/room/models"
import {ManageEventButtons} from "../components/ManageEventButtons"
import {IframeContent} from "../components/IframeContent"

interface CoffeeTableProps {
  id: number
  events: EventSlot[]
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
  const classes = useStyles()
  const iframeClasses = iframeUseStyles()
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
          {event.props.note && <Typography component="p">{event.props.note}</Typography>}
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

export const CoffeeTable = reduxConnect(mapStateToProps, mapDispatchToProps)(
  withRouter(CoffeeTableConnector)
)
