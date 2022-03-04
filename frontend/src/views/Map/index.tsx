import {
  Grid
} from "@material-ui/core"
import React from "react"
import {connect as reduxConnect} from "react-redux"
import {RouteComponentProps} from "react-router-dom"
import {withRouter} from "react-router"

import {RootState} from "../../stores/rootReducer"
import {Content} from "../components/Content/style"
import {Sidebar} from "../components/Sidebar"
import {Result} from "../../stores/search/models"
import {ResultGrid} from "../components/ResultGrid";
import {ResultMap} from "../components/ResultMap";
import {useStyles} from "./style";
import {ResultFilter} from "../components/ResultFilter";

interface MapProps {
  results: Result[]
}

function mapStateToProps(state: RootState) {
  return {
    results: state.search.results,
  }
}

const mapDispatchToProps = {
}

function MapConnector (props: MapProps & RouteComponentProps) {
  const { results } = props
  const classes = useStyles()

  return (
    <Grid
      className={classes.grid}
      container
    >
      <Content className="fullheight">
        <ResultMap results={results} />
      </Content>
      <Sidebar>
        <ResultFilter />
        <ResultGrid results={results} />
      </Sidebar>
    </Grid>
  )
}

export const Map = reduxConnect(mapStateToProps, mapDispatchToProps)(
  withRouter(MapConnector)
)
