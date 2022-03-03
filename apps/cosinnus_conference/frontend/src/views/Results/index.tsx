import {
  Grid,
  Typography
} from "@material-ui/core"
import React from "react"
import {connect as reduxConnect} from "react-redux"
import {RouteComponentProps} from "react-router-dom"
import {withRouter} from "react-router"

import {RootState} from "../../stores/rootReducer"
import {Content} from "../components/Content/style"
import {Main} from "../components/Main/style"
import {Loading} from "../components/Loading"
import {ManageRoomButtons} from "../components/ManageRoomButtons"
import {Room} from "../../stores/room/models"
import {IframeContent} from "../components/IframeContent"

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
  return (
    <Main container>
      {room && room.props.url && (
        <Content>
          <Typography component="h1">
            {room.props.title}
          </Typography>
          <IframeContent url={room.props.url} />
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
