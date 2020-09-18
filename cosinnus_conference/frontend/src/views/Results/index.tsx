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
import {Main} from "../components/Main/style"
import {Loading} from "../components/Loading"
import {ManageRoomButtons} from "../components/ManageRoomButtons"

interface ResultsProps {
  url: string
}

function mapStateToProps(state: RootState, _ownProps: ResultsProps) {
  return {
    url: state.room.props.url,
  }
}

const mapDispatchToProps = {
}

function ResultsConnector (props: ResultsProps & RouteComponentProps) {
  const { url } = props
  const iframeClasses = iframeUseStyles()
  return (
    <Main container>
      {url && (
        <Content>
          <Typography component="h1">
            <FormattedMessage id="Results" defaultMessage="Results" />
          </Typography>
          <div className={iframeClasses.resultsIframe}>
            <Iframe
              url={url}
              width="100%"
              height="100%"
            />
          </div>
          <ManageRoomButtons />
        </Content>
      ) || (
        <Content>
          <Loading />
        </Content>
      )}
    </Main>
  )
}

export const Results = reduxConnect(mapStateToProps, mapDispatchToProps)(
  withRouter(ResultsConnector)
)
