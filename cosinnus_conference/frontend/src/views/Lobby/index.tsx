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
import {fetchEvents} from "../../stores/events/effects"
import {DispatchedReduxThunkActionCreator} from "../../utils/types"
import {Event} from "../../stores/events/models"
import {Content} from "../components/Content/style"
import {EventList} from "../components/EventList"
import {Sidebar} from "../components/Sidebar"
import {ManageRoomButtons} from "../components/ManageRoomButtons"
import {Room} from "../../stores/room/models"
import {EventRoomState} from "../../stores/events/reducer"
import {Loading} from "../components/Loading"
import {Header} from "../components/Header"

interface LobbyProps {
  events: EventRoomState
  fetchEvents: DispatchedReduxThunkActionCreator<Promise<void>>
  room: Room
  url: string
}

function mapStateToProps(state: RootState) {
  return {
    events: state.events[state.room.props.id],
    room: state.room,
    url: state.room.props.url,
  }
}

const mapDispatchToProps = {
  fetchEvents
}

function LobbyConnector (props: LobbyProps & RouteComponentProps) {
  const { events, fetchEvents, room, url } = props
  // Rerender every minute
  const [time, setTime] = useState(new Date())
  useEffect(() => {
    const intervalId = setInterval(() => setTime(new Date()), 60000)
    return () => clearInterval(intervalId)
  }, [])

  if (!events && !(events && events.loading)) fetchEvents(true)

  return (
    <Grid container>
      <Content>
        <Header />
        <Typography component="h1">
          <FormattedMessage id="Agenda" />
        </Typography>
        {room.props.descriptionHtml && (
          <div className="description" dangerouslySetInnerHTML={{__html: room.props.descriptionHtml}} />
        )}
        {(events && events.events && events.events.length > 0 && <EventList events={events.events} showLinks={true} />)
          || (events && events.loading && <Loading />)
          || <Typography><FormattedMessage id="No events." /></Typography>
        }
        <ManageRoomButtons />
      </Content>
      {url && <Sidebar url={url} />}
    </Grid>
  )
}

export const Lobby = reduxConnect(mapStateToProps, mapDispatchToProps)(
  withRouter(LobbyConnector)
)
