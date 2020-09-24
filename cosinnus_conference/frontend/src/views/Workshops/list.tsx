import {
  Grid,
  Typography
} from "@material-ui/core"
import React from "react"
import {connect as reduxConnect} from "react-redux"
import {RouteComponentProps} from "react-router-dom"
import {withRouter} from "react-router"
import {FormattedMessage} from "react-intl"

import {RootState} from "../../stores/rootReducer"
import {DispatchedReduxThunkActionCreator} from "../../utils/types"
import {EventSlot} from "../../stores/events/models"
import {Content} from "../components/Content/style"
import {Sidebar} from "../components/Sidebar"
import {useStyles} from "./style"
import {EventCard} from "../components/EventCard"
import {fetchEvents} from "../../stores/events/effects"
import {ManageRoomButtons} from "../components/ManageRoomButtons"
import {Room} from "../../stores/room/models"

interface WorkshopsProps {
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

function WorkshopsConnector (props: WorkshopsProps & RouteComponentProps) {
  const { events, fetchEvents, room } = props
  if (!events) {
    fetchEvents()
  }
  const classes = useStyles()
  const currentWorkshops = events && events.filter((w) => w.isNow()) || []
  const upcomingWorkshops = events && events.filter((w) => !w.isNow()) || []
  return (
    <Grid container>
      <Content>
        <div className={classes.section}>
          {room.props.descriptionHtml && (
            <div className="description" dangerouslySetInnerHTML={{__html: room.props.descriptionHtml}} />
          )}
          <Typography component="h1"><FormattedMessage id="Happening now" /></Typography>
          {currentWorkshops.length > 0 && currentWorkshops.map((slot, index) => (
            <Grid container key={index} spacing={4}>
              {slot.props.events && slot.props.events.map((event, index) => (
              <Grid container item key={index} sm={6} className="now">
                <EventCard event={event} />
              </Grid>
              ))}
            </Grid>
            ))
            || <Typography><FormattedMessage id="No current workshops." /></Typography>
          }
        </div>
        <div className={classes.section}>
          <Typography component="h1"><FormattedMessage id="Upcoming workshops" /></Typography>
          {upcomingWorkshops.length > 0 && upcomingWorkshops.map((slot, index) => (
            <Grid container key={index} spacing={4}>
              {slot.props.events && slot.props.events.map((event, index) => (
              <Grid container item key={index} sm={6}>
                <EventCard event={event} />
              </Grid>
              ))}
            </Grid>
          ))
          || <Typography><FormattedMessage id="No upcoming workshops." /></Typography>
          }
        </div>
        <ManageRoomButtons />
      </Content>
      {room.props.url && <Sidebar url={room.props.url} />}
    </Grid>
  )
}

export const Workshops = reduxConnect(mapStateToProps, mapDispatchToProps)(
  withRouter(WorkshopsConnector)
)
