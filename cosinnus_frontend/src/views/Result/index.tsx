import {
  Grid,
  Typography
} from "@material-ui/core"
import React from "react"
import {connect as reduxConnect} from "react-redux"
import {RouteComponentProps} from "react-router-dom"
import {withRouter} from "react-router"

import {RootState} from "../../stores/rootReducer"
import {DispatchedReduxThunkActionCreator} from "../../utils/types"
import {Content} from "../components/Content/style"
import {Loading} from "../components/Loading"
import {Result as SearchResult} from "../../stores/search/models"
import {fetchSearchResults} from "../../stores/search/effects"

interface ResultProps {
  id: string
  results: SearchResult[]
}

function mapStateToProps(state: RootState) {
  return {
    results: state.search.results
  }
}

const mapDispatchToProps = {
}

function ResultConnector (props: ResultProps & RouteComponentProps) {
  const { id, results } = props
  const result = results.find((r) => r.props.id === id)
  return (
    <Grid container>
      {(result && (
        <Content>
          <Typography component="h1">{result.props.title}</Typography>
          {result.props.description && (
            <div className="description" dangerouslySetInnerHTML={{__html: result.props.description}} />
          )}
        </Content>
      ))
      || <Content><Loading /></Content>}
    </Grid>
  )
}

export const Result = reduxConnect(mapStateToProps, mapDispatchToProps)(
  withRouter(ResultConnector)
)
