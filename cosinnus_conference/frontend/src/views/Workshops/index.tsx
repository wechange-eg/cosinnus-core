import {
  Grid,
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
import {useStyles as useIframeStyles} from "../components/Iframe/style"
import {Content} from "../components/Content/style"
import {Sidebar} from "../components/Sidebar"
import {fetchWorkshops} from "../../stores/workshops/effects"
import {useStyles} from "./style"
import {EventCard} from "../components/EventCard"

interface WorkshopsProps {
  workshops: EventSlot[]

  fetchWorkshops: DispatchedReduxThunkActionCreator<Promise<void>>
}

function mapStateToProps(state: RootState) {
  return {
    workshops: state.workshops,
  }
}

const mapDispatchToProps = {
  fetchWorkshops
}

function WorkshopsConnector (props: WorkshopsProps & RouteComponentProps) {
  const { workshops, fetchWorkshops } = props
  if (!workshops) {
    fetchWorkshops()
  }
  const classes = useStyles()
  const iFrameclasses = useIframeStyles()
  const currentWorkshops = workshops && workshops.filter((w) => w.isNow()) || []
  const upcomingWorkshops = workshops && workshops.filter((w) => !w.isNow()) || []
  return (
    <Grid container>
      <Content>
        <div className={classes.section}>
          <Typography component="h1"><FormattedMessage id="Happening now" defaultMessage="Happening now" /></Typography>
          {currentWorkshops.length > 0 && currentWorkshops.map((slot, index) => (
            <Grid container key={index} spacing={4}>
              {slot.props.events && slot.props.events.map((event, index) => (
              <Grid item key={index} sm={6} className="now">
                <EventCard event={event} />
              </Grid>
              ))}
            </Grid>
            ))
            || <Typography><FormattedMessage id="No current workshops." defaultMessage="No current workshops." /></Typography>
          }
        </div>
        <div className={classes.section}>
          <Typography component="h1"><FormattedMessage id="Upcoming workshops" defaultMessage="Upcoming workshops" /></Typography>
          {upcomingWorkshops.length > 0 && upcomingWorkshops.map((slot, index) => (
            <Grid container key={index} spacing={4}>
              {slot.props.events && slot.props.events.map((event, index) => (
              <Grid item key={index} sm={6}>
                <EventCard event={event} />
              </Grid>
              ))}
            </Grid>
          ))
          || <Typography><FormattedMessage id="No upcoming workshops." defaultMessage="No upcoming workshops." /></Typography>
          }
        </div>
      </Content>
      <Sidebar elements={(
        <Iframe
          url="https://chat.wechange.de/channel/general"
          width="100%"
          height="100%"
          className={iFrameclasses.iframe}
        />
      )} />
    </Grid>
  )
}

export const Workshops = reduxConnect(mapStateToProps, mapDispatchToProps)(
  withRouter(WorkshopsConnector)
)
