import React, {useState} from "react"
import {Room} from "../../../stores/room/models"
import {Button, Dialog, DialogActions, DialogContent, DialogContentText, DialogTitle} from "@material-ui/core"
import {FontAwesomeIcon} from "@fortawesome/react-fontawesome"
import {faPen, faPlus, faTrashAlt} from "@fortawesome/free-solid-svg-icons"
import {FormattedMessage} from "react-intl"
import {connect as reduxConnect} from "react-redux"
import axios from "axios"
import Cookies from "js-cookie"

import {RootState} from "../../../stores/rootReducer"
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
  const [deleteOpen, setDeleteOpen] = useState(false);
  const classes = useStyles()
  if (!room.props.managementUrls) {
    return null
  }
  function deleteRoom() {
    axios.post(room.props.managementUrls.deleteRoom, {},{
      headers: {
        'X-CSRFTOKEN': Cookies.get('csrftoken'),
      },
      withCredentials: true
    }).then(_res => {
      window.location.href = "../"
    })
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
          <FormattedMessage id="Create event" />
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
          <FormattedMessage id="Edit room" />
        </Button>
      )}
      {room.props.managementUrls.deleteRoom && (
        <span>
          <Button
            variant="contained"
            disableElevation
            href="#"
            onClick={() => setDeleteOpen(true)}
          >
            <FontAwesomeIcon icon={faTrashAlt} />&nbsp;
            <FormattedMessage id="Delete room" />
          </Button>
          <Dialog
            open={deleteOpen}
            keepMounted
            onClose={() => setDeleteOpen(false)}
          >
            <DialogTitle><FormattedMessage id="Delete room" /></DialogTitle>
            <DialogContent>
              <DialogContentText>
                <FormattedMessage id="Are you sure you want to delete this room?" />
              </DialogContentText>
            </DialogContent>
            <DialogActions>
              <Button onClick={() => setDeleteOpen(false)} color="secondary">
                <FormattedMessage id="No" />
              </Button>
              <Button onClick={deleteRoom} color="secondary">
                <FormattedMessage id="Yes" />
              </Button>
            </DialogActions>
          </Dialog>
        </span>
      )}
    </div>
  )
}

export const ManageRoomButtons = reduxConnect(mapStateToProps, mapDispatchToProps)(
  ManageRoomButtonsConnector
)
