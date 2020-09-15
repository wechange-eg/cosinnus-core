import {
  Grid, ListItem, ListItemText,
  Typography
} from "@material-ui/core"
import React, {useState} from "react"
import {connect as reduxConnect} from "react-redux"
import {RouteComponentProps} from "react-router-dom"
import {withRouter} from "react-router"
import {FormattedMessage} from "react-intl";
import Iframe from "react-iframe"
import clsx from "clsx"

import {RootState} from "../../stores/rootReducer"
import {fetchEvents} from "../../stores/events/effects"
import {DispatchedReduxThunkActionCreator} from "../../utils/types"
import {EventSlot} from "../../stores/events/models"
import {useStyles} from "../components/Iframe/style"
import {formatTime} from "../../utils/events"
import {Content} from "../components/Content/style"
import {EventList} from "../components/EventList/style"
import {Sidebar} from "../components/Sidebar"

interface LobbyProps {
  events: EventSlot[]

  fetchEvents: DispatchedReduxThunkActionCreator<Promise<void>>
}

function mapStateToProps(state: RootState) {
  return {
    events: state.events,
  }
}

const mapDispatchToProps = {
  fetchEvents
}

function LobbyConnector (props: LobbyProps & RouteComponentProps) {
  const { events, fetchEvents } = props
  if (!events) {
    fetchEvents()
  }
  const classes = useStyles()
  return (
    <Grid container>
      <Content>
        <Typography component="h1"><FormattedMessage id="Agenda" defaultMessage="Agenda" /></Typography>
        {events && events.map((slot, index) => {
          const isNow = slot.isNow()
          return (
          <EventList
            key={index}
            className={clsx({
              ["now"]: isNow,
            })}
          >
            {!isNow && (
              <ListItem>
                <ListItemText primary={formatTime(slot.props.fromTime) + "-" + formatTime(slot.props.toTime)} />
                {slot.props.name && (
                  <ListItemText primary={slot.props.name && slot.props.name} />
                ) || (
                  <ListItemText primary={(
                    <Typography component="span">
                      {slot.props.events.length}&nbsp;
                      <FormattedMessage id="parallel events" defaultMessage="parallel events" />
                    </Typography>
                  )} />
                )}
              </ListItem>
            )}
            {slot.props.events && slot.props.events.map((event, index) => (
            <ListItem
              button
              key={event.props.id}
              href={event.props.url}
            >
              <ListItemText
                primary={event.props.roomName}
                secondary={isNow && <FormattedMessage id="Now" defaultMessage="Now" />}
              />
              <ListItemText primary={event.props.name} secondary={event.props.description} />
            </ListItem>
            ))}
          </EventList>
        )})
        || <Typography><FormattedMessage id="No events planned." defaultMessage="No events planned." /></Typography>
        }
      </Content>
      <Sidebar elements={(
        <Iframe
          url="https://chat.wechange.de/channel/general"
          width="100%"
          height="100%"
          className={classes.iframe}
        />
      )} />
    </Grid>
  )
}

export const Lobby = reduxConnect(mapStateToProps, mapDispatchToProps)(
  withRouter(LobbyConnector)
)
