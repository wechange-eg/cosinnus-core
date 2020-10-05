import React from "react"
import {Grid, Card, CardContent, CardActionArea, CardMedia, Typography} from "@material-ui/core"
import {RouteComponentProps} from "react-router-dom"
import {FormattedMessage} from "react-intl"

import {Event} from "../../../stores/events/models"
import {useStyles} from "./style"
import {ManageEventIcons} from "../ManageEventIcons"

export interface CoffeeTableProps {
  event: Event
  participantsCount: number
}

export function CoffeeTable(props: CoffeeTableProps & RouteComponentProps) {
  const { event, participantsCount } = props
  const classes = useStyles()
  if (!event) {
    return null
  }
  const participants = event.props.participants
  function renderParticipant(i: number) {
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
  const availablePlaces = participantsCount !== undefined && event.getAvailablePlaces(participantsCount)
  return (
    <Card className={classes.card}>
      <CardActionArea
        onClick={() => {
          if (availablePlaces === 0) return
          const url = event.getUrl()
          if (url) window.location.href = url
        }}
      >
        <CardContent>
          <Typography component="h3">{event.props.title}</Typography>
          <CardMedia
            component="img"
            alt={event.props.title}
            height="100"
            image={event.props.imageUrl}
            title={event.props.title}
          />
          {/*<Grid container spacing={1}>
          {Array.from(Array((6)), (v, i) => i + 1).map((_, i) => (
            renderParticipant(i)
          ))}
          </Grid>
          */}
          {participantsCount !== undefined && (
            (availablePlaces === null && (
              <Typography component="p">
                {participantsCount} <FormattedMessage id="participants" />
              </Typography>
            ))
            || (
              <Typography component="p">
                {availablePlaces} <FormattedMessage id="places left" />
              </Typography>
            )
          )}
          <ManageEventIcons event={event} />
        </CardContent>
      </CardActionArea>
    </Card>
  )
}
