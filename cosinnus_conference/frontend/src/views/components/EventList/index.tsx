import React, {useState} from "react"
import {
  Link,
  List,
  ListItem,
  ListItemText, Tab,
  Typography
} from "@material-ui/core"
import {TabContext, TabList} from "@material-ui/lab"
import TabPanel from "@material-ui/lab/TabPanel"
import {FormattedMessage} from "react-intl"
import clsx from "clsx"
import moment from "moment"

import {Event, EventDay} from "../../../stores/events/models"
import {formatTime, getCurrentDay, groupByDaysAndSlots, getTimezoneForUser} from "../../../utils/events"
import {EventIcons} from "../EventIcons"
import {useStyles} from "./style"

export interface EventListProps {
  events: Event[]
  showLinks: boolean
}

export function EventList(props: EventListProps) {
  const { events, showLinks } = props
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

  function renderEventListItem(event: Event) {
    return (
      <ListItem
        button
        key={event.props.id}
        onClick={() => {
          const url = event.getUrl()
          if (url) window.location.href = url
        }}
      >
        <ListItemText primary={event.props.room.title} className="room-title" />
        <ListItemText
          className="event-title"
          primary={event.props.title}
          secondary={<Typography component="span" dangerouslySetInnerHTML={{__html: event.getNoteOrPresenters()}} />}
        />
        <EventIcons event={event} showLinks={showLinks} />
      </ListItem>
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
                <Typography component="h1">
                  <FormattedMessage id="Happening now"/>
                </Typography>
                {currentSlots.map((slot, index) => (
                  <List
                    key={index}
                    className={clsx({
                      [classes.list]: true,
                      ["now"]: true,
                    })}
                  >
                    <ListItem>
                      <ListItemText
                        primary={formatTime(slot.props.fromDate) + "-" + formatTime(slot.props.toDate)}
                        secondary={"(" + getTimezoneForUser() + ")"}
                        secondaryTypographyProps={{
                          color: "textPrimary",
                          variant: "caption"
                        }}
                      />
                      {slot.props.isBreak && slot.props.title && (
                        <ListItemText primary={slot.props.title} />
                      ) || (
                        <ListItemText primary={slot.props.events.length > 1 && (
                          <Typography component="span">
                            {slot.props.events.length}&nbsp;
                            <FormattedMessage id="parallel events" />
                          </Typography>
                        )} />
                      )}
                    </ListItem>
                    {!slot.props.isBreak && slot.props.events && slot.props.events.map((event) => (
                      renderEventListItem(event)
                    ))}
                  </List>
                ))}
              </div>
            )}
            {upcomingSlots && upcomingSlots.length > 0 && (
              <div className={classes.section}>
                {upcomingSlots.map((slot, index) => (
                  <List
                    key={index}
                    className={classes.list}
                  >
                    <ListItem>
                      <ListItemText
                        primary={formatTime(slot.props.fromDate) + "-" + formatTime(slot.props.toDate)}
                        secondary={"(" + getTimezoneForUser() + ")"}
                        secondaryTypographyProps={{
                          color: "textPrimary",
                          variant: "caption"
                        }}
                        />
                      {slot.props.isBreak && slot.props.title && (
                        <ListItemText primary={slot.props.title} />
                      ) || (
                        <ListItemText primary={slot.props.events.length > 1 && (
                          <Typography component="span">
                            {slot.props.events.length}&nbsp;
                            <FormattedMessage id="parallel events" />
                          </Typography>
                        )} />
                      )}
                    </ListItem>
                    {!slot.props.isBreak && slot.props.events && slot.props.events.map((event) => (
                      renderEventListItem(event)
                    ))}
                  </List>
                ))}
              </div>
            )}
          </TabPanel>
        )
      })}
    </TabContext>
  )
}
