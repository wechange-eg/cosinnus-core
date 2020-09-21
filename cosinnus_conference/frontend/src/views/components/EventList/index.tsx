import React from "react"
import {FormattedMessage} from "react-intl"
import {
  List,
  ListItem,
  ListItemText,
  Typography
} from "@material-ui/core"
import {useStyles} from "./style"
import {useHistory} from "react-router"
import clsx from "clsx"

import {EventSlot} from "../../../stores/events/models"
import {formatTime} from "../../../utils/events"

export interface EventListProps {
  events: EventSlot[]
}

export function EventList(props: EventListProps) {
  const { events } = props
  const classes = useStyles()
  const history = useHistory()
  if (!events) {
    return null
  }
  return (events && events.map((slot, index) => {
    const isNow = slot.isNow()
    return (
    <List
      key={index}
      className={clsx({
        [classes.list]: true,
        ["now"]: isNow,
      })}
    >
      {!isNow && (
        <ListItem>
          <ListItemText primary={formatTime(slot.props.fromDate) + "-" + formatTime(slot.props.toDate)} />
          {slot.props.isBreak && slot.props.title && (
            <ListItemText primary={slot.props.title} />
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
      {!slot.props.isBreak && slot.props.events && slot.props.events.map((event) => (
      <ListItem
        button
        key={event.props.id}
        onClick={() => !event.props.isBreak && (window.location.href = event.getUrl())}
      >
        <ListItemText
          primary={event.props.room.title}
          secondary={isNow && <FormattedMessage id="Now" defaultMessage="Now" />}
        />
        <ListItemText primary={event.props.title} secondary={event.props.note} />
      </ListItem>
      ))}
    </List>
  )
  })
  || <Typography><FormattedMessage id="No events planned." defaultMessage="No events planned." /></Typography>
  )
}
