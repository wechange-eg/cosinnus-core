import React from "react"
import {FormattedMessage} from "react-intl"

import {Card, CardContent, CardMedia, Typography} from "@material-ui/core"
import {Event} from "../../../stores/events/models"

import {useStyles} from "./style"

export interface CoffeeTableProps {
  event: Event
}

export function CoffeeTable(props: CoffeeTableProps) {
  const { event } = props
  const classes = useStyles()
  if (!event) {
    return null
  }
  return (
    <Card className={classes.card}>
      <CardContent>
        <Typography component="h3">{event.props.name}</Typography>
        <CardMedia
          component="img"
          alt={event.props.name}
          height="100"
          image={event.props.imageUrl}
          title={event.props.name}
        />
        {event.props.participants && event.props.participants.map((participant, index) => (
          <Typography key={index} component="span">
            {participant.props.firstName} {participant.props.lastName},
            {participant.props.organisation}, {participant.props.location}
          </Typography>
        ))}
        <Typography component="p">
          x <FormattedMessage id="spots left" defaultMessage="spots left" />
        </Typography>
      </CardContent>
    </Card>
  )
}
