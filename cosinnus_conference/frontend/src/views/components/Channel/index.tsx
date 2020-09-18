import React from "react"
import {FormattedMessage} from "react-intl"
import {Grid, Card, CardContent, CardActionArea, CardMedia, Typography} from "@material-ui/core"
import {RouteComponentProps} from "react-router-dom"
import { useHistory } from "react-router";

import {Event} from "../../../stores/events/models"
import {useStyles} from "./style"

export interface ChannelProps {
  event: Event
}

export function Channel(props: ChannelProps & RouteComponentProps) {
  const { event } = props
  const classes = useStyles()
  const history = useHistory()
  if (!event) {
    return null
  }
  return (
    <Card className={classes.card}>
      <CardActionArea onClick={() => history.push("/" + event.props.id)}>
        <CardContent>
          <Typography component="span">{event.props.name}</Typography>
        </CardContent>
      </CardActionArea>
    </Card>
  )
}
