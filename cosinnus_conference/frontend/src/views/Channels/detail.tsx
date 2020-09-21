import {
  Typography
} from "@material-ui/core"
import React from "react"
import {connect as reduxConnect} from "react-redux"
import {RouteComponentProps} from "react-router-dom"
import {withRouter} from "react-router"
import {FormattedMessage} from "react-intl";
import Iframe from "react-iframe"

import {RootState} from "../../stores/rootReducer"
import {DispatchedReduxThunkActionCreator} from "../../utils/types"
import {useStyles as iframeUseStyles} from "../components/Iframe/style"
import {Content} from "../components/Content/style"
import {Main} from "../components/Main/style"
import {Loading} from "../components/Loading"
import {fetchEvents} from "../../stores/events/effects"
import {EventSlot} from "../../stores/events/models"
import {findEventById} from "../../utils/events"
import {ManageEventButtons} from "../components/ManageEventButtons"

interface ChannelProps {
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

function ChannelConnector (props: ChannelProps & RouteComponentProps) {
  const { id, events, fetchEvents } = props
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
            <FormattedMessage id="Networking" defaultMessage="Networking" />:&nbsp;
            {event.props.title}&nbsp;
          </Typography>
          <div className={iframeClasses.bbbIframe}>
            <Iframe
              url={event.props.url}
              width="100%"
              height="100%"
              allow="microphone *; camera *"
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

export const Channel = reduxConnect(mapStateToProps, mapDispatchToProps)(
  withRouter(ChannelConnector)
)
