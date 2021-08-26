import {
  Avatar, Button, CardActionArea, CardHeader, FormControl,
  Grid, InputLabel, MenuItem, Select, Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
  Typography
} from "@material-ui/core"
import React, {useEffect, useState} from "react"
import {connect as reduxConnect} from "react-redux"
import {RouteComponentProps} from "react-router-dom"
import {withRouter} from "react-router"
import {FormattedMessage} from "react-intl";
import { uniqBy } from "lodash"
import {FontAwesomeIcon} from "@fortawesome/react-fontawesome"
import {faCommentDots} from "@fortawesome/free-solid-svg-icons"

import {RootState} from "../../stores/rootReducer"
import {DispatchedReduxThunkActionCreator} from "../../utils/types"
import {Content} from "../components/Content/style"
import {useStyles} from "./style"
import {Room} from "../../stores/room/models"
import {fetchParticipants} from "../../stores/participants/effects"
import {Participant} from "../../stores/participants/models"
import {ManageRoomButtons} from "../components/ManageRoomButtons"
import {Notification} from "../components/Notification"

interface ParticipantsProps {
  participants: Participant[]
  fetchParticipants: DispatchedReduxThunkActionCreator<Promise<void>>
  room: Room
}

function mapStateToProps(state: RootState) {
  return {
    participants: state.participants,
    room: state.room,
  }
}

const mapDispatchToProps = {
  fetchParticipants
}

interface ParticipantsTableProps {
  participants: Participant[]
}

function ParticipantsTable (props: ParticipantsTableProps) {
  const { participants } = props
  const classes = useStyles()
  return (participants && participants.length > 0 && (
    <TableContainer className={classes.tableContainer}>
      <Table className={classes.table} aria-label="simple table">
        <TableHead>
          <TableRow>
            <TableCell><FormattedMessage id="Name" /></TableCell>
            <TableCell><FormattedMessage id="Organization" /></TableCell>
            <TableCell><FormattedMessage id="Country" /></TableCell>
            <TableCell align="right"></TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {participants.map((participant, index) => (
            <TableRow key={index}>
              <TableCell component="th" scope="row">
                <CardHeader
                  avatar={
                    <Avatar
                      alt={participant.getFullName()}
                      src={participant.getAvatarUrl()}
                      variant="square" />
                  }
                  title={participant.getFullName()}
                />
              </TableCell>
              <TableCell>{participant.props.organization}</TableCell>
              <TableCell>{participant.props.country}</TableCell>
              <TableCell align="right">
                <Button
                  variant="contained"
                  disableElevation
                  href=""
                  onClick={() => {
                    const url = participant.getUrl()
                    if (url) window.location.href = url
                  }}
                >
                  <FontAwesomeIcon icon={faCommentDots} />&nbsp;
                  <FormattedMessage id="Contact" />
                </Button>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
    )
    || <Typography><FormattedMessage id="No participants." /></Typography>
  )
}

function ParticipantsConnector (props: ParticipantsProps & RouteComponentProps) {
  const { participants, fetchParticipants, room } = props
  const [country, setCountry] = useState("")
  const classes = useStyles()
  let filteredParticipants: Participant[] = participants
  if (!participants || participants.length == 0) {
    fetchParticipants()
  }

  function handleCountryChange(event: object) {
    setCountry(event.target.value)
  }

  const countries: string[] = uniqBy(participants, p => p.props.country).map(p => p.props.country)
  if (country !== "") {
    filteredParticipants = participants.filter(p => p.props.country === country)
  }
  return (
    <Grid container>
      <Content>
        <Notification />
        <Typography component="h1">{room.props.title}</Typography>
        {room.props.descriptionHtml && (
          <div className="description" dangerouslySetInnerHTML={{__html: room.props.descriptionHtml}} />
        )}
        <FormControl className={classes.formControl}>
          <InputLabel><FormattedMessage id="Filter by country" /></InputLabel>
          <Select
            value={country}
            onChange={handleCountryChange}
          >
            {countries.map((country) => (
              <MenuItem key={country} value={country}>{country}</MenuItem>
            ))}
          </Select>
        </FormControl>
        <ParticipantsTable participants={filteredParticipants} />
        <ManageRoomButtons />
      </Content>
    </Grid>
  )
}

export const Participants = reduxConnect(mapStateToProps, mapDispatchToProps)(
  withRouter(ParticipantsConnector)
)
