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
import {EventSlot} from "../../stores/events/models"
import {useStyles as iframeUseStyles} from "../components/Iframe/style"
import {Content} from "../components/Content/style"
import {useStyles} from "./style"
import {Loading} from "../components/Loading"
import {Main} from "../components/Main/style"
import {fetchEvents} from "../../stores/events/effects"
import {findEventById} from "../../utils/events"
import {Room} from "../../stores/room/reducer"
import {ManageEventButtons} from "../components/ManageEventButtons"

interface CoffeeTableProps {
  id: number
  events: EventSlot[]
  fetchEvents: DispatchedReduxThunkActionCreator<Promise<void>>
}

function mapStateToProps(state: RootState, _ownProps: CoffeeTableProps) {
  return {
    events: state.events[state.room.props.id]
  }
}

const mapDispatchToProps = {
  fetchEvents: fetchEvents
}

function CoffeeTableConnector (props: CoffeeTableProps & RouteComponentProps) {
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
            <FormattedMessage id="Coffee table" defaultMessage="Coffee table" />:&nbsp;
            {event.props.title}&nbsp;
            (<FormattedMessage id="Coffee table" defaultMessage="limited to 6 people" />)
          </Typography>
          <div className={iframeClasses.bbbIframe}>
            <Iframe
              url={event.props.url}
              width="100%"
              height="100%"
              allow="geolocation; microphone; camera"
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

export const CoffeeTable = reduxConnect(mapStateToProps, mapDispatchToProps)(
  withRouter(CoffeeTableConnector)
)
