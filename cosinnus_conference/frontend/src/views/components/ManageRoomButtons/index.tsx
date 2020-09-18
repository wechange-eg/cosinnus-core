import React, {useState} from "react"
import {Room} from "../../../stores/room/models"
import {Button} from "@material-ui/core"
import {FontAwesomeIcon} from "@fortawesome/react-fontawesome"
import {faCog, faPen, faPlus, faTrashAlt} from "@fortawesome/free-solid-svg-icons"
import {FormattedMessage} from "react-intl"
import {RootState} from "../../../stores/rootReducer"
import {fetchEvents} from "../../../stores/events/effects"
import {connect as reduxConnect} from "react-redux"
import {withRouter} from "react-router"
import {useStyles} from "./style"

interface ManageRoomButtonsProps {
  room: Room
}

function mapStateToProps(state: RootState) {
  return {
    room: state.room,
  }
}

const mapDispatchToProps = {
}

export function ManageRoomButtonsConnector(props: ManageRoomButtonsProps) {
  const {room} = props
  const classes = useStyles()
  if (!room.props.managementUrls) {
    return null
  }
  return (
    <div className={classes.buttons}>
      <Button
        variant="contained"
        color="primary"
        disableElevation
        href="#"
        onClick={() => window.location.href = room.props.managementUrls.create}
      >
        <FontAwesomeIcon icon={faPlus} />&nbsp;
        <FormattedMessage id="Create room" defaultMessage="Create room" />
      </Button>
      <Button
        variant="contained"
        color="primary"
        disableElevation
        href="#"
        onClick={() => window.location.href = room.props.managementUrls.update}
      >
        <FontAwesomeIcon icon={faPen} />&nbsp;
        <FormattedMessage id="Edit room" defaultMessage="Edit room" />
      </Button>
      <Button
        variant="contained"
        color="primary"
        disableElevation
        href="#"
        onClick={() => window.location.href = room.props.managementUrls.delete}
      >
        <FontAwesomeIcon icon={faTrashAlt} />&nbsp;
        <FormattedMessage id="Delete room" defaultMessage="Delete room" />
      </Button>
    </div>
  )
}

export const ManageRoomButtons = reduxConnect(mapStateToProps, mapDispatchToProps)(
  ManageRoomButtonsConnector
)
