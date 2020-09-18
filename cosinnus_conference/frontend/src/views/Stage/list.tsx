import {
  Grid, ListItem, ListItemText,
  Typography
} from "@material-ui/core"
import React, {useState} from "react"
import {connect as reduxConnect} from "react-redux"
import {RouteComponentProps} from "react-router-dom"
import {useHistory, withRouter} from "react-router"
import {FormattedMessage} from "react-intl";
import Iframe from "react-iframe"
import clsx from "clsx"

import {RootState} from "../../stores/rootReducer"
import {fetchEvents} from "../../stores/events/effects"
import {DispatchedReduxThunkActionCreator} from "../../utils/types"
import {EventSlot} from "../../stores/events/models"
import {formatTime} from "../../utils/events"
import {Content} from "../components/Content/style"
import {EventList} from "../components/EventList/style"
import {Sidebar} from "../components/Sidebar"
import {useStyles as iframeUseStyles} from "./style"

interface StageProps {
  events: EventSlot[]
  fetchEvents: DispatchedReduxThunkActionCreator<Promise<void>>
  url: string
}

function mapStateToProps(state: RootState, _ownProps: StageProps) {
  return {
    events: state.events[window.conferenceRoom],
    url: state.conference && state.conference.rooms[window.conferenceRoom].url,
  }
}

const mapDispatchToProps = {
  fetchEvents: fetchEvents
}

function StageConnector (props: StageProps & RouteComponentProps) {
  const { events, fetchEvents, url } = props
  const history = useHistory()
  if (!events) {
    fetchEvents(window.conferenceRoom)
  }
  const discussions: Event[] = []

  const iframeClasses = iframeUseStyles()
  return (
    <Grid container>
      <Content>
        <Typography component="h1"><FormattedMessage id="Agenda" defaultMessage="Agenda" /></Typography>
        {events && events.map((slot, index) => (
          <EventList key={index} className="now">
            {slot.props.events.map((event, index) => (
            <ListItem
              button
              key={event.props.id}
              href="#"
              onClick={() => history.push("/" + event.props.id)}
            >
              <ListItemText primary={event.props.roomName} />
              <ListItemText primary={event.props.name} secondary={event.props.description} />
            </ListItem>
            ))}
          </EventList>
        )
        || <Typography>
          <FormattedMessage id="No current events in this room." defaultMessage="No current events in this room." />
        </Typography>
        )}
        {discussions && discussions.map((slot, index) => {
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
                <ListItemText primary={formatTime(slot.props.fromTime) + "-" + formatTime(slot.props.toTime)} />
                {slot.props.name && (
                  <ListItemText primary={slot.props.name && slot.props.name} />
                ) || (
                  <ListItemText primary={(
                    <Typography component="span">
                      {slot.props.events && slot.props.events.length}&nbsp;
                      <FormattedMessage id="parallel events" defaultMessage="parallel discussions" />
                    </Typography>
                  )} />
                )}
              </ListItem>
            )}
            {slot.props.events && slot.props.events.map((discussion, index) => (
            <ListItem
              button
              key={discussion.props.id}
              href={discussion.props.url}
            >
              <ListItemText
                primary={discussion.props.roomName}
                secondary={isNow && <FormattedMessage id="Now" defaultMessage="Now" />}
              />
              <ListItemText primary={discussion.props.name} secondary={discussion.props.description} />
            </ListItem>
            ))}
          </EventList>
        )})
        || <Typography>
          <FormattedMessage
            id="No discussions planned in this room."
            defaultMessage="No discussions planned in this room."
          />
        </Typography>
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

export const Stage = reduxConnect(mapStateToProps, mapDispatchToProps)(
  withRouter(StageConnector)
)
