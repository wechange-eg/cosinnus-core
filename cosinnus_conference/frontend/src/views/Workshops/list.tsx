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
import {Event} from "../../stores/events/models"
import {Content} from "../components/Content/style"
import {Sidebar} from "../components/Sidebar"
import {fetchEvents} from "../../stores/events/effects"
import {ManageRoomButtons} from "../components/ManageRoomButtons"
import {Room} from "../../stores/room/models"
import {EventGrid} from "../components/EventGrid"
import {EventRoomState} from "../../stores/events/reducer"
import {Loading} from "../components/Loading"

interface WorkshopsProps {
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

function WorkshopsConnector (props: WorkshopsProps & RouteComponentProps) {
  const { events, fetchEvents, room } = props
  // Rerender every minute
  const [time, setTime] = useState(new Date())
  useEffect(() => { setInterval(() => setTime(new Date()), 60000) })

  if (!events) {
    fetchEvents()
  }
  return (
    <Grid container>
      <Content>
        <Typography component="h1"><FormattedMessage id="Agenda" /></Typography>
        {room.props.descriptionHtml && (
          <div className="description" dangerouslySetInnerHTML={{__html: room.props.descriptionHtml}} />
        )}
        {(events && events.events && events.events.length > 0 && <EventGrid events={events.events} />)
        || (events && events.loading && <Loading />)
        || <Typography><FormattedMessage id="No workshops." /></Typography>
        }
        <ManageRoomButtons />
      </Content>
      {room.props.url && <Sidebar url={room.props.url} />}
    </Grid>
  )
}

export const Workshops = reduxConnect(mapStateToProps, mapDispatchToProps)(
  withRouter(WorkshopsConnector)
)
