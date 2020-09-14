import {
  Badge, Box, Button, Drawer,
  Grid, List, ListItem, ListItemText,
  Typography
} from "@material-ui/core"
import React, {useState} from "react"
import {connect as reduxConnect} from "react-redux"
import {RouteComponentProps} from "react-router-dom"
import {withRouter} from "react-router"
import {FormattedMessage} from "react-intl";
import Iframe from "react-iframe"

import {RootState} from "../../stores/rootReducer"
import {fetchEvents} from "../../stores/events/effects"
import {DispatchedReduxThunkActionCreator} from "../../utils/types"
import clsx from "clsx"

import {EventSlot} from "../../stores/events/models"
import {filterCurrentAndRoom, formatTime} from "../../utils/events"
import {Content} from "../components/Content/style"
import {EventList} from "../components/EventList/style"
import {Sidebar} from "../components/Sidebar/index"
import {useStyles} from "./style"
import {EventSlot} from "../../stores/discussions/models"
import {fetchDiscussions} from "../../stores/discussions/effects"

interface StageProps {
  events: EventSlot[]
  discussions: EventSlot[]

  fetchEvents: DispatchedReduxThunkActionCreator<Promise<void>>
  fetchDiscussions: DispatchedReduxThunkActionCreator<Promise<void>>
}

function mapStateToProps(state: RootState) {
  return {
    events: state.events,
    discussions: state.discussions,
  }
}

const mapDispatchToProps = {
  fetchEvents,
  fetchDiscussions
}

function StageConnector (props: StageProps & RouteComponentProps) {
  const { events, fetchEvents } = props
  const { discussions, fetchDiscussions } = props
  if (!events) {
    fetchEvents()
  }
  if (!discussions) {
    fetchDiscussions()
  }

  const classes = useStyles()
  const eventSlot = filterCurrentAndRoom(events, window.conferenceView)
  return (
    <Grid container>
      <Content>
        <Typography component="h1"><FormattedMessage id="Agenda" defaultMessage="Agenda" /></Typography>
        {eventSlot && (
          <EventList className="now">
            {eventSlot.props.events.map((event, index) => (
            <ListItem
              button
              key={event.props.id}
              href={event.props.url}
            >
              <ListItemText primary={event.props.roomName} />
              <ListItemText primary={event.props.name} secondary={event.props.description} />
            </ListItem>
            ))}
          </EventList>
        )
        || <Typography>
          <FormattedMessage id="No current events in this room." defaultMessage="No current events in this room." />
        </Typography>
        }
        {discussions && discussions.map((slot, index) => {
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
                      {slot.props.events && slot.props.events.length}&nbsp;
                      <FormattedMessage id="parallel events" defaultMessage="parallel discussions" />
                    </Typography>
                  )} />
                )}
              </ListItem>
            )}
            {slot.props.events && slot.props.events.map((discussion, index) => (
            <ListItem
              button
              key={discussion.props.id}
              href={discussion.props.url}
            >
              <ListItemText
                primary={discussion.props.roomName}
                secondary={isNow && <FormattedMessage id="Now" defaultMessage="Now" />}
              />
              <ListItemText primary={discussion.props.name} secondary={discussion.props.description} />
            </ListItem>
            ))}
          </EventList>
        )})
        || <Typography>
          <FormattedMessage
            id="No discussions planned in this room."
            defaultMessage="No discussions planned in this room."
          />
        </Typography>
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

export const Stage = reduxConnect(mapStateToProps, mapDispatchToProps)(
  withRouter(StageConnector)
)
