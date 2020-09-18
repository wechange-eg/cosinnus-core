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
import {useStyles as iframeUseStyles} from "../components/Iframe/style"
import {Content} from "../components/Content/style"
import {Sidebar} from "../components/Sidebar"
import {useStyles} from "./style"
import {CoffeeTable} from "../components/CoffeeTable"
import {fetchEvents} from "../../stores/events/effects"
import {ManageRoomButtons} from "../components/ManageRoomButtons"

interface CoffeeTablesProps {
  events: EventSlot[]
  fetchEvents: DispatchedReduxThunkActionCreator<Promise<void>>
  url: string
}

function mapStateToProps(state: RootState, _ownProps: CoffeeTablesProps) {
  return {
    events: state.events[state.room.props.id],
    url: state.room.url,
  }
}

const mapDispatchToProps = {
  fetchEvents: fetchEvents
}

function CoffeeTablesConnector (props: CoffeeTablesProps & RouteComponentProps) {
  const { events, fetchEvents, url } = props
  if (!events) {
    fetchEvents()
  }
  const classes = useStyles()
  const iframeClasses = iframeUseStyles()
  return (
    <Grid container>
      <Content>
        <div className={classes.section}>
          <Typography component="h1"><FormattedMessage id="Happening now" defaultMessage="Happening now" /></Typography>
          {events && events.length > 0 && (
            <Grid container spacing={4}>
              {events.map((slot, index) => (
                slot.props.events.map((event, eventIndex) => (
                <Grid item key={index + "-" + eventIndex} sm={6} className="now">
                  <CoffeeTable event={event} />
                </Grid>
                ))
              ))}
            </Grid>
          )
          || <Typography><FormattedMessage id="No current coffee tables." defaultMessage="No current coffee tables." /></Typography>
        }
        </div>
        {/*
        <div className={classes.section}>
          <Button href="#">
            <FontAwesomeIcon icon={faPlus} />&nbsp;
            <FormattedMessage id="Start your own Coffee Table" defaultMessage="Start your own Coffee Table" />
          </Button>
        </div>
        */}
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

export const CoffeeTables = reduxConnect(mapStateToProps, mapDispatchToProps)(
  withRouter(CoffeeTablesConnector)
)
