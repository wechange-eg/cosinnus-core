import React from "react"
import {Card, CardContent, CardActionArea, Typography} from "@material-ui/core"
import {RouteComponentProps} from "react-router-dom"

import {Event} from "../../../stores/events/models"
import {useStyles} from "./style"

export interface ChannelProps {
  event: Event
}

export function Channel(props: ChannelProps & RouteComponentProps) {
  const { event } = props
  const classes = useStyles()
  if (!event) {
    return null
  }
  return (
    <Card className={classes.card}>
      <CardActionArea
        onClick={() => {
          const url = event.getUrl()
          if (url) window.location.href = url
        }}
      >
        <CardContent>
          <Typography component="span">{event.props.title}</Typography>
        </CardContent>
      </CardActionArea>
    </Card>
  )
}
