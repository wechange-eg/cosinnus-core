import React, {useState} from "react"
import {Button, Dialog, DialogActions, DialogContent, DialogContentText, DialogTitle, Link} from "@material-ui/core"
import {FontAwesomeIcon} from "@fortawesome/react-fontawesome"
import {faPen, faPlus, faTrashAlt} from "@fortawesome/free-solid-svg-icons"
import {FormattedMessage} from "react-intl"
import Cookies from "js-cookie"
import {useStyles} from "./style"
import axios from "axios"

import {Event} from "../../../stores/events/models"

interface ManageEventIconsProps {
  event: Event
}

export function ManageEventIcons(props: ManageEventIconsProps) {
  const {event} = props
  const classes = useStyles()
  const [deleteOpen, setDeleteOpen] = useState(false);
  if (!event.props.managementUrls) {
    return null
  }
  function deleteEvent() {
    axios.post(event.props.managementUrls.deleteEvent, {},{
      headers: {
        'X-CSRFTOKEN': Cookies.get('csrftoken'),
      },
      withCredentials: true
    }).then(res => {
      window.location.href = "../"
    })
  }
  return (
    <div className={classes.icons}>
      {event.props.managementUrls.updateEvent && (
        <Link
          href="#"
          onClick={e => {
            e.stopPropagation()
            window.location.href = event.props.managementUrls.updateEvent
          }}
        >
          <FontAwesomeIcon icon={faPen} />
        </Link>
      )}
      {event.props.managementUrls.deleteEvent && (
        <span>
          <Link
            href="#"
            onClick={e => {
              e.stopPropagation()
              setDeleteOpen(true)
            }}
          >
            <FontAwesomeIcon icon={faTrashAlt} />
          </Link>
          <Dialog
            open={deleteOpen}
            keepMounted
            onClose={() => setDeleteOpen(false)}
          >
            <DialogTitle><FormattedMessage id="Delete Event" defaultMessage="Delete Event" /></DialogTitle>
            <DialogContent>
              <DialogContentText>
                <FormattedMessage
                  id="Are you sure you want to delete this event?"
                  defaultMessage="Are you sure you want to delete this event?"
                />
              </DialogContentText>
            </DialogContent>
            <DialogActions>
              <Button onClick={() => setDeleteOpen(false)} color="primary">
                <FormattedMessage id="No" defaultMessage="No" />
              </Button>
              <Button onClick={deleteEvent} color="primary">
                <FormattedMessage id="Yes" defaultMessage="Yes" />
              </Button>
            </DialogActions>
          </Dialog>
        </span>
      )}
    </div>
  )
}
