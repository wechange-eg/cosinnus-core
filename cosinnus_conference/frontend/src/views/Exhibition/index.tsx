import {
  Typography
} from "@material-ui/core"
import React, {Component} from "react"
import {connect as reduxConnect} from "react-redux"
import {RouteComponentProps} from "react-router-dom"
import {withRouter} from "react-router"
import {FormattedMessage} from "react-intl";

import {
  ExhibitionContainer
} from "./style"
import {RootState} from "../../stores/rootReducer"

function mapStateToProps(state: RootState) {
  return {
    user: state.user,
  }
}

const mapDispatchToProps = {
}

class ExhibitionConnector extends Component<RouteComponentProps> {

  render() {
    return (
      <ExhibitionContainer>
        <Typography>
          <FormattedMessage id="Exhibition" defaultMessage="Exhibition"/>
        </Typography>
      </ExhibitionContainer>
    )
  }
}

export const Exhibition = reduxConnect(mapStateToProps, mapDispatchToProps)(
  withRouter(ExhibitionConnector)
)
