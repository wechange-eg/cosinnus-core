import {
  Grid,
  Typography
} from "@material-ui/core"
import React from "react"
import {connect as reduxConnect} from "react-redux"
import {RouteComponentProps} from "react-router-dom"
import {withRouter} from "react-router"
import {FormattedMessage} from "react-intl"

import {RootState} from "../../stores/rootReducer"
import {Content} from "../components/Content/style"
import {Result} from "../../stores/search/models"
import {ResultList} from "../components/ResultList";

interface SearchProps {
  results: Result[]
}

function mapStateToProps(state: RootState) {
  return {
    results: state.search.results,
  }
}

const mapDispatchToProps = {
}

function SearchConnector (props: SearchProps & RouteComponentProps) {
  const { results } = props

  return (
    <Grid container>
      <Content>
        <Typography component="h1"><FormattedMessage id="Search results" /></Typography>
        <ResultList results={results} />
      </Content>
    </Grid>
  )
}

export const Search = reduxConnect(mapStateToProps, mapDispatchToProps)(
  withRouter(SearchConnector)
)
