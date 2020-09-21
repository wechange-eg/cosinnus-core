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
      {room.props.managementUrls.createEvent && (
        <Button
          variant="contained"
          disableElevation
          href="#"
          onClick={() => window.location.href = room.props.managementUrls.createEvent}
        >
          <FontAwesomeIcon icon={faPlus} />&nbsp;
          <FormattedMessage id="Create event" defaultMessage="Create event" />
        </Button>
      )}
      {room.props.managementUrls.updateRoom && (
        <Button
          variant="contained"
          disableElevation
          href="#"
          onClick={() => window.location.href = room.props.managementUrls.updateRoom}
        >
          <FontAwesomeIcon icon={faPen} />&nbsp;
          <FormattedMessage id="Edit room" defaultMessage="Edit room" />
        </Button>
      )}
      {room.props.managementUrls.deleteRoom && (
        <Button
          variant="contained"
          disableElevation
          href="#"
          onClick={() => window.location.href = room.props.managementUrls.deleteRoom}
        >
          <FontAwesomeIcon icon={faTrashAlt} />&nbsp;
          <FormattedMessage id="Delete room" defaultMessage="Delete room" />
        </Button>
      )}
    </div>
  )
}

export const ManageRoomButtons = reduxConnect(mapStateToProps, mapDispatchToProps)(
  ManageRoomButtonsConnector
)
