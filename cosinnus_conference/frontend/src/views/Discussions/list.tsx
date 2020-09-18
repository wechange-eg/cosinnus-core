import {
  Grid, ListItem, ListItemText,
  Typography
} from "@material-ui/core"
import React from "react"
import {connect as reduxConnect} from "react-redux"
import {RouteComponentProps} from "react-router-dom"
import {withRouter, useHistory} from "react-router"
import {FormattedMessage} from "react-intl";
import Iframe from "react-iframe"
import clsx from "clsx"

import {RootState} from "../../stores/rootReducer"
import {DispatchedReduxThunkActionCreator} from "../../utils/types"
import {EventSlot} from "../../stores/events/models"
import {useStyles as iframeUseStyles} from "../components/Iframe/style"
import {formatTime} from "../../utils/events"
import {Content} from "../components/Content/style"
import {EventList} from "../components/EventList/style"
import {Sidebar} from "../components/Sidebar"
import {fetchEvents} from "../../stores/events/effects"

interface DiscussionsProps {
  events: EventSlot[]
  fetchEvents: DispatchedReduxThunkActionCreator<Promise<void>>
  url: string
}

function mapStateToProps(state: RootState, _ownProps: DiscussionsProps) {
  return {
    events: state.events[window.conferenceRoomSlug],
    url: state.conference && state.conference.rooms[window.conferenceRoomSlug].url,
  }
}

const mapDispatchToProps = {
  fetchEvents: fetchEvents
}

function DiscussionsConnector (props: DiscussionsProps & RouteComponentProps) {
  const { events, fetchEvents, url } = props
  const history = useHistory()
  if (!events) {
    fetchEvents(window.conferenceRoomId)
  }
  const iframeClasses = iframeUseStyles()
  return (
    <Grid container>
      <Content>
        <Typography component="h1"><FormattedMessage id="Agenda" defaultMessage="Agenda" /></Typography>
        {events && events.map((slot, index) => {
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
                <ListItemText primary={formatTime(slot.props.fromDate) + "-" + formatTime(slot.props.toDate)} />
                {slot.props.title && (
                  <ListItemText primary={slot.props.title && slot.props.title} />
                ) || (
                  <ListItemText primary={(
                    <Typography component="span">
                      {slot.props.events.length}&nbsp;
                      <FormattedMessage id="parallel discussions" defaultMessage="parallel discussions" />
                    </Typography>
                  )} />
                )}
              </ListItem>
            )}
            {slot.props.events && slot.props.events.map((event, index) => (
            <ListItem
              button
              key={event.props.id}
              href="#"
              onClick={() => history.push("/" + event.props.id)}
            >
              <ListItemText
                primary={event.props.room.title}
                secondary={isNow && <FormattedMessage id="Now" defaultMessage="Now" />}
              />
              <ListItemText primary={event.props.title} secondary={event.props.note} />
            </ListItem>
            ))}
          </EventList>
        )})
        || <Typography><FormattedMessage id="No discussions planned." defaultMessage="No discussions planned." /></Typography>
        }
      </Content>
      <Sidebar elements={(
        <Iframe
          url={url}
          width="100%"
          height="100%"
          className={iframeClasses.sidebarIframe}
        />
      )} />
    </Grid>
  )
}

export const Discussions = reduxConnect(mapStateToProps, mapDispatchToProps)(
  withRouter(DiscussionsConnector)
)
