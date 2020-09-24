import {
  Typography
} from "@material-ui/core"
import React from "react"
import {connect as reduxConnect} from "react-redux"
import {RouteComponentProps} from "react-router-dom"
import {withRouter} from "react-router"

import {RootState} from "../../stores/rootReducer"
import {DispatchedReduxThunkActionCreator} from "../../utils/types"
import {Content} from "../components/Content/style"
import {Main} from "../components/Main/style"
import {Loading} from "../components/Loading"
import {Participant as ParticipantModel} from "../../stores/participants/models"
import {fetchParticipants} from "../../stores/participants/effects"
import {IframeContent} from "../components/IframeContent"

interface ParticipantProps {
  id: number
  participants: ParticipantModel[]
  fetchParticipants: DispatchedReduxThunkActionCreator<Promise<void>>
}

function mapStateToProps(state: RootState) {
  return {
    participants: state.participants,
  }
}

const mapDispatchToProps = {
  fetchParticipants
}

function ParticipantConnector (props: ParticipantProps & RouteComponentProps) {
  const { id, participants, fetchParticipants } = props
  let participant: ParticipantModel = null
  if (participants) {
    participant = participants.find(p => p.props.id === id)
  } else {
    fetchParticipants()
  }
  return (
    <Main container>
      {participant && (
        <Content>
          <Typography component="h1">{participant.getFullName()}</Typography>
          <Typography component="p">{participant.props.organisation}, {participant.props.country}</Typography>
          <IframeContent url={participant.props.chatUrl} />
        </Content>
      ) || (
        <Content>
          <Loading />
        </Content>
      )}
    </Main>
  )
}

export const Participant = reduxConnect(mapStateToProps, mapDispatchToProps)(
  withRouter(ParticipantConnector)
)
