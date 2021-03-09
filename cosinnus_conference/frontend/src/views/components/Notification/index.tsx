import React, {useState} from "react"
import {
  Link
} from "@material-ui/core"
import Alert from '@material-ui/lab/Alert';
import {connect} from "react-redux"
import {FontAwesomeIcon} from "@fortawesome/react-fontawesome"
import {
  faBuilding, faCheck,
  faCircle,
  faCoffee, faCog,
  faComments,
  faHandshake,
  faHome, faUser,
  faUsers, faDoorClosed, faUsersCog, faCalendar, faChalkboardTeacher, faBars
} from '@fortawesome/free-solid-svg-icons'
import {IconDefinition} from "@fortawesome/fontawesome-common-types"
import {FormattedMessage} from "react-intl"
import clsx from "clsx"

import {RootState} from "../../../stores/rootReducer"
import {useStyles} from "./style"
import {Room} from "../../../stores/room/models"
import {Conference} from "../../../stores/conference/models"
import {Participant} from "../../../stores/participants/models"

interface NotificationProps {
  conference: Conference
}

function mapStateToProps(state: RootState) {
  return {
    conference: state.conference
  }
}

const mapDispatchToProps = {
}

function NotificationConnector(props: NotificationProps) {
  const { conference } = props
  const classes = useStyles()
  if (!conference) {
    return null
  }
  if (!conference.props.headerNotification || !conference.props.headerNotification.notificationText) {
    return null
  }
  return (
    <div className={classes.notification}>
      {conference.props.headerNotification.notificationText && (
        <Alert
          severity="warning"
          action={
            <Link className={classes.link} href={conference.props.headerNotification.linkUrl} >
              {conference.props.headerNotification.linkText}
            </Link>
          }>
          <span className="description" dangerouslySetInnerHTML={{__html: conference.props.headerNotification.notificationText}} />
        </Alert>
      )}
    </div>
  )
}

export const Notification = connect(mapStateToProps, mapDispatchToProps)(NotificationConnector)
