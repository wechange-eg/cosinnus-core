import {
  Grid, ListItem, ListItemText,
  Typography
} from "@material-ui/core"
import React from "react"
import {connect as reduxConnect} from "react-redux"
import {RouteComponentProps} from "react-router-dom"
import {withRouter} from "react-router"
import {FormattedMessage} from "react-intl";
import Iframe from "react-iframe"
import clsx from "clsx"

import {RootState} from "../../stores/rootReducer"
import {DispatchedReduxThunkActionCreator} from "../../utils/types"
import {EventSlot} from "../../stores/events/models"
import {useStyles as iframeUseStyles, useStyles} from "../components/Iframe/style"
import {findEventById} from "../../utils/events"
import {Content} from "../components/Content/style"
import {Main} from "../components/Main/style"
import {Loading} from "../components/Loading"
import {fetchEvents} from "../../stores/events/effects"
import {ManageEventButtons} from "../components/ManageEventButtons"

interface DiscussionProps {
  id: number
  events: EventSlot[]
  fetchEvents: DispatchedReduxThunkActionCreator<Promise<void>>
}

function mapStateToProps(state: RootState) {
  return {
    events: state.events[state.room.props.id],
  }
}

const mapDispatchToProps = {
  fetchEvents
}

function DiscussionConnector (props: DiscussionProps & RouteComponentProps) {
  const { id, events, fetchEvents } = props
  const classes = useStyles()
  const iframeClasses = iframeUseStyles()
  let event = null
  if (events) {
    event = findEventById(events, id)
  } else {
    fetchEvents()
  }
  return (
    <Main container>
      {event && (
        <Content>
          <Typography component="h1">
            <FormattedMessage id="Discussion" defaultMessage="Discussion" />:&nbsp;
            {event.props.title}
          </Typography>
          <div className={iframeClasses.bbbIframe}>
            <Iframe
              url={event.props.url}
              width="100%"
              height="100%"
            />
          </div>
          <ManageEventButtons event={event} />
        </Content>
      ) || (
        <Content>
          <Loading />
        </Content>
      )}
    </Main>
  )
}

export const Discussion = reduxConnect(mapStateToProps, mapDispatchToProps)(
  withRouter(DiscussionConnector)
)
