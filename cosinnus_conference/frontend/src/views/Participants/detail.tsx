import {
  Grid, ListItem, ListItemText,
  Typography
} from "@material-ui/core"
import React from "react"
import {connect as reduxConnect} from "react-redux"
import {RouteComponentProps} from "react-router-dom"
import {withRouter} from "react-router"
import {FormattedMessage} from "react-intl";
import Iframe from "react-iframe"
import clsx from "clsx"

import {RootState} from "../../stores/rootReducer"
import {DispatchedReduxThunkActionCreator} from "../../utils/types"
import {EventSlot} from "../../stores/events/models"
import {useStyles as iframeUseStyles, useStyles} from "../components/Iframe/style"
import {findEventById} from "../../utils/events"
import {Content} from "../components/Content/style"
import {Main} from "../components/Main/style"
import {Loading} from "../components/Loading"
import {fetchEvents} from "../../stores/events/effects"
import {ManageEventButtons} from "../components/ManageEventButtons"
import {Participant} from "../../stores/participants/models"
import {fetchParticipants} from "../../stores/participants/effects"

interface ParticipantProps {
  id: number
  participants: Participant[]
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
  const classes = useStyles()
  const iframeClasses = iframeUseStyles()
  let participant: Participant = null
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
          <div className={iframeClasses.bbbIframe}>
            <Iframe
              url={participant.props.chatUrl}
              width="100%"
              height="100%"
              allow="microphone *; camera *"
            />
          </div>
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
