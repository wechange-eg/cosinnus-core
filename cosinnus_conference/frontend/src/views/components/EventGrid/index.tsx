import React, {useState} from "react"
import {FormattedMessage} from "react-intl"
import {Card, CardActionArea, CardContent, Grid, Tab, Tabs, Typography} from "@material-ui/core"
import TabPanel from "@material-ui/lab/TabPanel"
import clsx from "clsx"
import {TabContext, TabList} from "@material-ui/lab"
import moment from "moment"

import {Event, EventDay} from "../../../stores/events/models"
import {formatTime, getCurrentDay, groupByDaysAndSlots, getTimezoneForUser} from "../../../utils/events"
import {EventIcons} from "../EventIcons"
import {useStyles} from "./style"
import {EventParticipants} from "../../../stores/eventParticipants/reducer"

export interface EventGridProps {
  events: Event[]
  eventParticipants: EventParticipants
}

export function EventGrid(props: EventGridProps) {
  const { events, eventParticipants } = props
  const classes = useStyles()
  const days = groupByDaysAndSlots(events)
  const [ currentDay, setCurrentDay] = useState(getCurrentDay(days))
  if (!events) return null

  function getDayLabel(day: EventDay) {
    return (
      (day.isToday() && <FormattedMessage id="Today" />)
      || (day.isTomorrow() && <FormattedMessage id="Tomorrow" />)
      || moment(day.props.date).format('DD.MM.')
    )
  }

  function getEventParticipantCount(event: Event) {
    return eventParticipants && eventParticipants[event.props.id]
  }

  function renderEventCard(event: Event) {
    const isNow = event.isNow()
    const participantsCount = getEventParticipantCount(event)
    return (
      <Card className={clsx({
        [classes.card]: true,
        [classes.break]: event.props.isBreak,
      })}>
        <CardActionArea
          classes={{
            root: classes.actionArea,
            focusHighlight: classes.focusHighlight
          }}
          onClick={() => {
            const url = event.getUrl()
            if (url) window.location.href = url
          }}
        >
          <CardContent>
            <div className={classes.left}>
              {isNow && (
                <Typography component="span">
                  <FormattedMessage id="Now" />
                  {"-" + formatTimeZoneAwareTime(event.props.toDate)} ({getTimezoneForUser(event.props.fromDate)})
                </Typography>
              ) || (
                <Typography component="span">
                  {formatTime(event.props.fromDate) + "-" + formatTime(event.props.toDate)} ({getTimezoneForUser(event.props.fromDate)})
                </Typography>
              )}
              <Typography component="span">
                {event.props.title}
              </Typography>
              <Typography component="span" dangerouslySetInnerHTML={{__html: event.getNoteOrPresenters()}} />
            </div>
            <div className={classes.right}>
              {isNow && (
                <div>
                  <Typography component="span">
                    {event.getMinutesLeft()}&nbsp;
                    <FormattedMessage id="minutes left" />
                  </Typography>
                  {participantsCount !== undefined && (
                    <Typography component="p">
                      {participantsCount}&nbsp;
                      <FormattedMessage id="participants" />
                    </Typography>
                  )}
                  <Typography component="p"> </Typography>
                </div>
              ) || (
                <div>
                  {/*
                  <Link href="#" className={classes.link}>
                    <FontAwesomeIcon icon={faUserPlus} />
                  </Link>
                  <Link href="#" className={classes.link}>
                    <FontAwesomeIcon icon={faHeart} />
                  </Link>
                  <Link href="#" className={classes.link}>
                    <FontAwesomeIcon icon={faCalendarPlus} />
                  </Link>
                  */}
                </div>
              )}
            </div>
            <EventIcons event={event} />
          </CardContent>
        </CardActionArea>
      </Card>
    )
  }

  return (
    <TabContext value={currentDay}>
      <TabList onChange={(e, day: string) => setCurrentDay(day)} className={classes.tabList}>
        {days.map(day => (
          <Tab
            key={day.props.date}
            value={day.props.date}
            label={getDayLabel(day)}
          />
        ))}
      </TabList>
      {days.map(day => {
        const currentSlots = day.getCurrentSlots()
        const upcomingSlots = day.getUpcomingSlots()
        return (
          <TabPanel key={day.props.date} value={day.props.date} className={classes.tabPanel}>
            {currentSlots && currentSlots.length > 0 && (
              <div className={classes.section}>
                <Typography component="h1"><FormattedMessage id="Happening now"/></Typography>
                <Grid container spacing={4}>
                  {currentSlots.map((slot, index) => (
                    slot.props.events.map((event, eventIndex) => (
                      <Grid item key={index + "-" + eventIndex} sm={6} className="now">
                        {renderEventCard(event)}
                      </Grid>
                    ))
                  ))}
                </Grid>
              </div>
            )}
            {upcomingSlots && upcomingSlots.length > 0 && (
              <div className={classes.section}>
                {currentSlots && currentSlots.length > 0 && (
                  <Typography component="h1"><FormattedMessage id="Upcoming"/></Typography>
                )}
                <Grid container spacing={4}>
                  {upcomingSlots.map((slot, index) => (
                    slot.props.events.map((event, eventIndex) => (
                      <Grid item key={index + "-" + eventIndex} sm={6}>
                        {renderEventCard(event)}
                      </Grid>
                    ))
                  ))}
                </Grid>
              </div>
            )}
          </TabPanel>
        )
      })}
    </TabContext>
  )
}
