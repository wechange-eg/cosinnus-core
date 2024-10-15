import {
    Button,
    Divider,
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
import {FontAwesomeIcon} from "@fortawesome/react-fontawesome";
import {faExternalLinkAlt} from "@fortawesome/free-solid-svg-icons";
import {FormattedMessage} from "react-intl";
import {useStyles} from "../components/EventGrid/style";

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
  const classes = useStyles()
  return (
    <Main container>
      {room && room.props.url && (
          <Content>
              <Typography component="h1">
                  {room.props.title}
              </Typography>
              <div className={classes.section}>
                      <Button
                          variant="contained"
                          disableElevation
                          href={room.props.url}
                          target="_blank"
                      >
                          <FontAwesomeIcon icon={faExternalLinkAlt}/>&nbsp;
                          <FormattedMessage id="Open Result Project"/>
                      </Button>
              </div>
              <Divider/>
              <ManageRoomButtons/>
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
