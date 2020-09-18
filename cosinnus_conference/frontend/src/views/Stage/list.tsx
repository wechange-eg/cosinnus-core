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
import {useStyles as iframeUseStyles} from "../components/Iframe/style"
import {ManageRoomButtons} from "../components/ManageRoomButtons"

interface StageProps {
  events: EventSlot[]
  fetchEvents: DispatchedReduxThunkActionCreator<Promise<void>>
  url: string
}

function mapStateToProps(state: RootState) {
  return {
    events: state.events[state.room.props.id],
    url: state.room.url,
  }
}

const mapDispatchToProps = {
  fetchEvents: fetchEvents
}

function StageConnector (props: StageProps & RouteComponentProps) {
  const { events, fetchEvents, url } = props
  const history = useHistory()
  if (!events) {
    fetchEvents()
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
                      <FormattedMessage id="parallel events" defaultMessage="parallel events" />
                    </Typography>
                  )} />
                )}
              </ListItem>
            )}
            {slot.props.events && slot.props.events.map((event, index) => (
            <ListItem
              button
              key={event.props.id}
              href={event.props.url}
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
        || <Typography><FormattedMessage id="No events planned." defaultMessage="No events planned." /></Typography>
        }
        <ManageRoomButtons />
      </Content>
      {url && (
        <Sidebar elements={(
          <Iframe
            url={url}
            width="100%"
            height="100%"
            className={iframeClasses.sidebarIframe}
          />
        )} />
      )}
    </Grid>
  )
}

export const Stage = reduxConnect(mapStateToProps, mapDispatchToProps)(
  withRouter(StageConnector)
)
