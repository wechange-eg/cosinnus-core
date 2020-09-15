import React from "react"
import {FormattedMessage} from "react-intl"
import {Grid, Card, CardContent, CardMedia, Typography} from "@material-ui/core"

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
  const participants = event.props.participants

  function renderParticipant(i) {
    return (
      <Grid item key={i} sm={6} className={classes.participant}>
        {participants && (participants.length > i) && (
          <span>
            <Typography component="span">
              {participants[i].props.firstName} {participants[i].props.lastName},
            </Typography>
            <Typography component="span">
              {participants[i].props.organisation}, {participants[i].props.location}
            </Typography>
          </span>
        ) || <span /> }
      </Grid>
    )
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
        <Grid container spacing={1}>
        {Array.from(Array((6)), (v, i) => i + 1).map((_, i) => (
          renderParticipant(i)
        ))}
        </Grid>
        <Typography component="p">
          x <FormattedMessage id="spots left" defaultMessage="spots left" />
        </Typography>
      </CardContent>
    </Card>
  )
}
