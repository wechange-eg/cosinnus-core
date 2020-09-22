import React from "react"
import {
  ListItemText, Drawer, Typography, List, ListItem, Badge, Button, Divider
} from "@material-ui/core"
import {connect} from "react-redux"
import {FontAwesomeIcon} from "@fortawesome/react-fontawesome"
import {
  faBuilding, faCheck,
  faCircle,
  faCoffee, faCog,
  faComments,
  faHandshake,
  faHome, faUser,
  faUsers, faDoorClosed, faUsersCog, faCalendar, faChalkboardTeacher
} from '@fortawesome/free-solid-svg-icons'
import {IconDefinition} from "@fortawesome/fontawesome-common-types"
import {FormattedMessage} from "react-intl"

import {RootState} from "../../../stores/rootReducer"
import {useStyles} from "./style"
import {Room} from "../../../stores/room/models"
import {Conference} from "../../../stores/conference/models"
import {Participant} from "../../../stores/participants/models"

interface NavProps {
  conference: Conference
  participants: Participant[]
  room: Room
}

function mapStateToProps(state: RootState) {
  return {
    conference: state.conference,
    participants: state.participants,
    room: state.room,
  }
}

const mapDispatchToProps = {
}

function NavConnector(props: NavProps) {
  const { conference, participants, room } = props
  const classes = useStyles()
  if (!conference) {
    return null
  }
  function getIconByType(type: string) {
    const icons: { [t: string]: IconDefinition } = {
      "lobby": faHome,
      "stage": faUser,
      "discussions": faComments,
      "workshops": faChalkboardTeacher,
      "coffee_tables": faCoffee,
      "networking": faHandshake,
      "exhibition": faBuilding,
      "results": faCheck,
      "participants": faUsers,
    }
    return icons[type] || faCircle
  }
  return (
    <Drawer
      className={classes.drawer}
      variant="persistent"
      anchor="left"
      open={true}
      classes={{
        paper: classes.drawerPaper,
      }}
    >
      <div className={classes.drawerHeader}>
        <Typography component="h3">{conference.props.name}</Typography>
        <Typography component="h4">{conference.props.description}</Typography>
      </div>
      <List>
        {conference.props.rooms.map((navRoom) => (
            <ListItem
              button
              key={navRoom.props.id}
              href={"../" + navRoom.props.slug + "/"}
              selected={room && navRoom.props.id === room.props.id}
              className={classes.listItem}
            >
              <FontAwesomeIcon icon={getIconByType(navRoom.props.type)}/>&nbsp;
              <ListItemText
                primary={navRoom.props.title}
                secondary={!navRoom.props.isVisible && <FormattedMessage id="hidden" defaultMessage="hidden" />}
              />
              <Badge badgeContent={navRoom.props.count} className={classes.badge} />
            </ListItem>
        ))}
        {(conference.props.managementUrls.manageConference || conference.props.managementUrls.manageRooms ) && (
          <Divider />
        )}
        {conference.props.managementUrls.manageConference && (
        <ListItem
          button
          href={conference.props.managementUrls.manageConference}
          className={classes.listItem}
        >
          <FontAwesomeIcon icon={faCog} />&nbsp;
          <ListItemText primary={<FormattedMessage id="Manage Conference" defaultMessage="Manage Conference" />} />
        </ListItem>
        )}
        {conference.props.managementUrls.manageRooms && (
        <ListItem
          button
          href={conference.props.managementUrls.manageRooms}
          className={classes.listItem}
        >
          <FontAwesomeIcon icon={faDoorClosed} />&nbsp;
          <ListItemText primary={<FormattedMessage id="Manage Rooms" defaultMessage="Manage Rooms" />} />
        </ListItem>
        )}
        {conference.props.managementUrls.manageEvents && (
        <ListItem
          button
          href={conference.props.managementUrls.manageEvents}
          className={classes.listItem}
        >
          <FontAwesomeIcon icon={faCalendar} />&nbsp;
          <ListItemText primary={<FormattedMessage id="Manage Events" defaultMessage="Manage Events" />} />
        </ListItem>
        )}
      </List>
    </Drawer>
  )
}

export const Nav = connect(mapStateToProps, mapDispatchToProps)(NavConnector)
