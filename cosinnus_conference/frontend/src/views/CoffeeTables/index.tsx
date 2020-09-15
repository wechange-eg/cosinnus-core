import {
  Button,
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
import {Event} from "../../stores/events/models"
import {useStyles as useIframeStyles} from "../components/Iframe/style"
import {Content} from "../components/Content/style"
import {Sidebar} from "../components/Sidebar"
import {fetchCoffeeTables} from "../../stores/coffee_tables/effects"
import {useStyles} from "./style"
import {CoffeeTable} from "../components/CoffeeTable"
import {FontAwesomeIcon} from "@fortawesome/react-fontawesome"
import {faPlus} from "@fortawesome/free-solid-svg-icons"

interface CoffeeTablesProps {
  coffeeTables: Event[]

  fetchCoffeeTables: DispatchedReduxThunkActionCreator<Promise<void>>
}

function mapStateToProps(state: RootState) {
  return {
    coffeeTables: state.coffee_tables,
  }
}

const mapDispatchToProps = {
  fetchCoffeeTables
}

function CoffeeTablesConnector (props: CoffeeTablesProps & RouteComponentProps) {
  const { coffeeTables, fetchCoffeeTables } = props
  if (!coffeeTables) {
    fetchCoffeeTables()
  }
  const classes = useStyles()
  const iFrameClasses = useIframeStyles()
  return (
    <Grid container>
      <Content>
        <div className={classes.section}>
          <Typography component="h1"><FormattedMessage id="Happening now" defaultMessage="Happening now" /></Typography>
          {coffeeTables && coffeeTables.length > 0 && (
            <Grid container spacing={4}>
              {coffeeTables.map((event, index) => (
              <Grid item key={index} sm={6} className="now">
                <CoffeeTable event={event} />
              </Grid>
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
      </Content>
      <Sidebar elements={(
        <Iframe
          url="https://chat.wechange.de/channel/general"
          width="100%"
          height="100%"
          className={iFrameClasses.iframe}
        />
      )} />
    </Grid>
  )
}

export const CoffeeTables = reduxConnect(mapStateToProps, mapDispatchToProps)(
  withRouter(CoffeeTablesConnector)
)
