import React, {useState} from "react"
import {Button, Dialog, DialogActions, DialogContent, DialogContentText, DialogTitle, Link} from "@material-ui/core"
import {FontAwesomeIcon} from "@fortawesome/react-fontawesome"
import {faPen, faTrashAlt, faClipboard} from "@fortawesome/free-solid-svg-icons"
import {FormattedMessage} from "react-intl"
import Cookies from "js-cookie"
import axios from "axios"

import {Event} from "../../../stores/events/models"
import {useStyles} from "./style"

interface EventButtonsProps {
  event: Event
}

export function EventButtons(props: EventButtonsProps) {
  const {event} = props
  const classes = useStyles()
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [invitationDialogOpen, setInvitationDialogOpen] = useState(false);
  const [invitationDialogText, setInvitationDialogText] = useState("");
  if (!event.props.managementUrls) {
    return null
  }
  function deleteEvent(e) {
    e.stopPropagation()
    axios.post(event.props.managementUrls.deleteEvent, {},{
      headers: {
        'X-CSRFTOKEN': Cookies.get('csrftoken'),
      },
      withCredentials: true
    }).then(res => {
      window.location.href = "../"
    })
  }
  function copyInvitationToClipboard(e, guest: boolean) {
    fetch(`/api/v2/conferences/invitation/?object_type=event&object_id=${event.props.id}&guest=${guest === true}`, {
      method: "GET"
    }).then(response => {
      if (response.status === 200) {
        response.json().then((data: JSON) => {
          if (data.invitation) {
            navigator.clipboard.writeText(data.invitation).then(() => {
              setInvitationDialogText(data.alert_text);
              setInvitationDialogOpen(true)
            })
          }
        })
      }
    })
  }
  return (
    <div className={classes.buttons}>
      {event.props.managementUrls.updateEvent && (
        <Button
          variant="contained"
          disableElevation
          href="#"
          onClick={() => window.location.href = event.props.managementUrls.updateEvent}
        >
          <FontAwesomeIcon icon={faPen} />&nbsp;
          <FormattedMessage id="Edit event" />
        </Button>
      )}
      {event.props.managementUrls.deleteEvent && (
        <span>
          <Button
            variant="contained"
            disableElevation
            href="#"
            onClick={(e) => {
              e.stopPropagation()
              setDeleteOpen(true)
            }}
          >
            <FontAwesomeIcon icon={faTrashAlt} />&nbsp;
            <FormattedMessage id="Delete event" />
          </Button>
          <Dialog
            open={deleteOpen}
            keepMounted
            onClose={() => setDeleteOpen(false)}
          >
            <DialogTitle>
              <FormattedMessage id="Delete event" />
            </DialogTitle>
            <DialogContent>
              <DialogContentText classes={{root: classes.dialogText}}>
                <FormattedMessage id="Are you sure you want to delete this event?" />
              </DialogContentText>
            </DialogContent>
            <DialogActions>
              <Button
                onClick={(e) => {
                  e.stopPropagation()
                  setDeleteOpen(false)
                }}
                color="secondary"
              >
                <FormattedMessage id="No" />
              </Button>
              <Button onClick={deleteEvent} color="secondary">
                <FormattedMessage id="Yes" />
              </Button>
            </DialogActions>
          </Dialog>
        </span>
      )}

      <Button
          variant="contained"
          href="#"
          onClick={(e) => {copyInvitationToClipboard(e, false);}}
      >
        <FontAwesomeIcon icon={faClipboard} />&nbsp;
        <FormattedMessage id="Copy invitation" />
      </Button>
      {event.props.userIsAdmin && (
        <Button
            variant="contained"
            href="#"
            onClick={(e) => {copyInvitationToClipboard(e, true); }}
        >
          <FontAwesomeIcon icon={faClipboard} />&nbsp;
          <FormattedMessage id="Copy guest invitation" />
        </Button>
      )}
      <Dialog
          open={invitationDialogOpen}
          onClose={() => setInvitationDialogOpen(false)}
      >
        <DialogContent>
          <DialogContentText classes={{root: classes.dialogText}}>
            <FormattedMessage id={invitationDialogText} />
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={(e) => {setInvitationDialogOpen(false)}} color="secondary">
            <FormattedMessage id="OK" />
          </Button>
        </DialogActions>
      </Dialog>
    </div>
  )
}
