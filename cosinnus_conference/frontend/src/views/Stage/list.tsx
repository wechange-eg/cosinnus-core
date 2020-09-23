import {
  Grid, ListItem, ListItemText,
  Typography
} from "@material-ui/core"
import React, {useState} from "react"
import {connect as reduxConnect} from "react-redux"
import {RouteComponentProps} from "react-router-dom"
import {useHistory, withRouter} from "react-router"
import {FormattedMessage} from "react-intl";
import Iframe from "react-iframe"
import clsx from "clsx"

import {RootState} from "../../stores/rootReducer"
import {fetchEvents} from "../../stores/events/effects"
import {DispatchedReduxThunkActionCreator} from "../../utils/types"
import {EventSlot} from "../../stores/events/models"
import {formatTime} from "../../utils/events"
import {Content} from "../components/Content/style"
import {EventList} from "../components/EventList"
import {Sidebar} from "../components/Sidebar"
import {useStyles as iframeUseStyles} from "../components/Iframe/style"
import {ManageRoomButtons} from "../components/ManageRoomButtons"
import {Room} from "../../stores/room/models"

interface StageProps {
  events: EventSlot[]
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
  fetchEvents: fetchEvents
}

function StageConnector (props: StageProps & RouteComponentProps) {
  const { events, fetchEvents, room } = props
  if (!events) {
    fetchEvents()
  }
  return (
    <Grid container>
      <Content>
        <Typography component="h1"><FormattedMessage id="Agenda" defaultMessage="Agenda" /></Typography>
        {room.props.descriptionHtml && (
          <div className="description" dangerouslySetInnerHTML={{__html: room.props.descriptionHtml}} />
        )}
        <EventList events={events} />
        <ManageRoomButtons />
      </Content>
      {room.props.url && <Sidebar url={room.props.url} />}
    </Grid>
  )
}

export const Stage = reduxConnect(mapStateToProps, mapDispatchToProps)(
  withRouter(StageConnector)
)
