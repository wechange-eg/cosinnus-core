import React from "react"
import {FormattedMessage} from "react-intl"
import {Card, CardContent, Link, Typography} from "@material-ui/core"
import {FontAwesomeIcon} from "@fortawesome/react-fontawesome"
import {faCalendarPlus, faHeart, faUserPlus} from "@fortawesome/free-solid-svg-icons"

import {Event} from "../../../stores/events/models"
import {formatTime} from "../../../utils/events"
import {useStyles} from "./style"

export interface EventCardProps {
  event: Event
}

export function EventCard(props: EventCardProps) {
  const { event } = props
  const classes = useStyles()
  if (!event) {
    return null
  }
  const isNow = event.isNow()
  return (
    <Card className={classes.card}>
      <CardContent>
        <div className={classes.left}>
          {isNow && (
            <Typography component="span">
              <FormattedMessage id="Now" defaultMessage="Now" />
              {"-" + formatTime(event.props.toTime)}
            </Typography>
          ) || (
            <Typography component="span">
              {formatTime(event.props.fromTime) + "-" + formatTime(event.props.toTime)}
            </Typography>
          )}
          <Typography component="span">
            {event.props.name}
          </Typography>
          <Typography component="p">
            {event.props.description}
          </Typography>
        </div>
        <div className={classes.right}>
          {isNow && (
            <div>
              <Typography component="span">
                {event.getMinutesLeft()}&nbsp;
                <FormattedMessage id="minutes left" defaultMessage="minutes left" />
              </Typography>
              <Typography component="p">
                {event.props.participantsCount}&nbsp;
                <FormattedMessage id="participants" defaultMessage="participants" />
              </Typography>
              <Typography component="p"> </Typography>
            </div>
          ) || (
            <div>
              <Link href="#" className={classes.link}>
                <FontAwesomeIcon icon={faUserPlus} />
              </Link>
              <Link href="#" className={classes.link}>
                <FontAwesomeIcon icon={faHeart} />
              </Link>
              <Link href="#" className={classes.link}>
                <FontAwesomeIcon icon={faCalendarPlus} />
              </Link>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
