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
import {Room} from "../../stores/room/models"

interface ResultsProps {
  room: Room
}

function mapStateToProps(state: RootState) {
  return {
    room: state.room,
  }
}

const mapDispatchToProps = {
}

function ResultsConnector (props: ResultsProps & RouteComponentProps) {
  const { room } = props
  const iframeClasses = iframeUseStyles()
  return (
    <Main container>
      {room && room.props.url && (
        <Content>
          <Typography component="h1">
            {room.props.title}
          </Typography>
          <div className={iframeClasses.resultsIframe}>
            <Iframe
              url={room.props.url}
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
