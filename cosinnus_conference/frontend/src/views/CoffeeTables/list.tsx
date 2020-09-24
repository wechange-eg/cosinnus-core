import {
  Grid,
  Typography
} from "@material-ui/core"
import React from "react"
import {connect as reduxConnect} from "react-redux"
import {RouteComponentProps} from "react-router-dom"
import {withRouter} from "react-router"
import {FormattedMessage} from "react-intl";

import {RootState} from "../../stores/rootReducer"
import {DispatchedReduxThunkActionCreator} from "../../utils/types"
import {EventSlot} from "../../stores/events/models"
import {Content} from "../components/Content/style"
import {Sidebar} from "../components/Sidebar"
import {useStyles} from "./style"
import {CoffeeTable} from "../components/CoffeeTable"
import {fetchEvents} from "../../stores/events/effects"
import {ManageRoomButtons} from "../components/ManageRoomButtons"
import {Room} from "../../stores/room/models"

interface CoffeeTablesProps {
  events: EventSlot[]
  fetchEvents: DispatchedReduxThunkActionCreator<Promise<void>>
  room: Room
}

function mapStateToProps(state: RootState, _ownProps: CoffeeTablesProps) {
  return {
    events: state.events[state.room.props.id],
    room: state.room,
  }
}

const mapDispatchToProps = {
  fetchEvents: fetchEvents
}

function CoffeeTablesConnector (props: CoffeeTablesProps & RouteComponentProps) {
  const { events, fetchEvents, room } = props
  if (!events) {
    fetchEvents()
  }
  const classes = useStyles()
  return (
    <Grid container>
      <Content>
        <div className={classes.section}>
          <Typography component="h1"><FormattedMessage id="Happening now" /></Typography>
          {room.props.descriptionHtml && (
            <div className="description" dangerouslySetInnerHTML={{__html: room.props.descriptionHtml}} />
          )}
          {events && events.length > 0 && (
            <Grid container spacing={4}>
              {events.map((slot, index) => (
                slot.props.events.map((event, eventIndex) => (
                <Grid item key={index + "-" + eventIndex} sm={6} className="now">
                  <CoffeeTable event={event} />
                </Grid>
                ))
              ))}
            </Grid>
          )
          || <Typography><FormattedMessage id="No current coffee tables." /></Typography>
        }
        </div>
        <ManageRoomButtons />
      </Content>
      {room.props.url && <Sidebar url={room.props.url} />}
    </Grid>
  )
}

export const CoffeeTables = reduxConnect(mapStateToProps, mapDispatchToProps)(
  withRouter(CoffeeTablesConnector)
)
