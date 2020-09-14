import {
  Typography
} from "@material-ui/core"
import React, {Component} from "react"
import {connect as reduxConnect} from "react-redux"
import {RouteComponentProps} from "react-router-dom"
import {withRouter} from "react-router"
import {FormattedMessage} from "react-intl";

import {
  NetworkingContainer
} from "./style"
import {RootState} from "../../stores/rootReducer"

function mapStateToProps(state: RootState) {
  return {
    user: state.user,
  }
}

const mapDispatchToProps = {
}

class NetworkingConnector extends Component<RouteComponentProps> {

  render() {
    return (
      <NetworkingContainer>
        <Typography>
          <FormattedMessage id="Networking" defaultMessage="Networking"/>
        </Typography>
      </NetworkingContainer>
    )
  }
}

export const Networking = reduxConnect(mapStateToProps, mapDispatchToProps)(
  withRouter(NetworkingConnector)
)
