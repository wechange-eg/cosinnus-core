import React, {useState} from "react"
import {
  ListItemText,
  Drawer,
  Typography,
  List,
  ListItem,
  Badge,
  Divider,
  Link,
  Hidden
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
  const [open, setOpen] = useState(false)
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
        {conference.props.avatar && (
          <Hidden smDown>
          <img
            src={conference.props.avatar}
            alt={conference.props.name}
            className={classes.logo}
          />
          </Hidden>
        )}
        <Typography component="h3">{conference.props.name}</Typography>
        <Typography component="h4">{conference.props.description}</Typography>
        <Link
          className={classes.toggleMenuButton}
          href="#"
          onClick={() => setOpen(!open)}
        >
          <FontAwesomeIcon icon={faBars} />
        </Link>
      </div>
      <List className={clsx({
        [classes.collapsed]: !open,
      })}>
        {conference.props.rooms.map((navRoom) => (
            <ListItem
              button
              key={navRoom.props.id}
              component="a"
              href={"../" + navRoom.props.slug + "/"}
              selected={room && navRoom.props.id === room.props.id}
              className={classes.listItem}
            >
              <FontAwesomeIcon icon={getIconByType(navRoom.props.type)}/>&nbsp;
              <ListItemText
                primary={navRoom.props.title}
                secondary={!navRoom.props.isVisible && (
                  <FormattedMessage id="hidden" />
                )}
              />
              <Badge badgeContent={navRoom.props.count} className={classes.badge} max={999} />
            </ListItem>
        ))}
        {(conference.props.managementUrls.manageConference || conference.props.managementUrls.manageRooms
          || conference.props.managementUrls.manageEvents || conference.props.managementUrls.manageMemberships ) && (
          <Divider classes={{
              root: classes.divider,
            }}
          />
        )}
        {conference.props.managementUrls.manageConference && (
        <ListItem
          button
          component="a"
          href={conference.props.managementUrls.manageConference}
          className={classes.listItem}
        >
          <FontAwesomeIcon icon={faCog} />&nbsp;
          <ListItemText primary={
            <FormattedMessage id="Manage conference" />
          } />
        </ListItem>
        )}
        {conference.props.managementUrls.manageRooms && (
        <ListItem
          button
          component="a"
          href={conference.props.managementUrls.manageRooms}
          className={classes.listItem}
        >
          <FontAwesomeIcon icon={faDoorClosed} />&nbsp;
          <ListItemText primary={<FormattedMessage id="Manage rooms" />} />
        </ListItem>
        )}
        {conference.props.managementUrls.manageEvents && (
        <ListItem
          button
          component="a"
          href={conference.props.managementUrls.manageEvents}
          className={classes.listItem}
        >
          <FontAwesomeIcon icon={faCalendar} />&nbsp;
          <ListItemText primary={<FormattedMessage id="Manage events" />} />
        </ListItem>
        )}
        {conference.props.managementUrls.manageMemberships && (
        <ListItem
          button
          component="a"
          href={conference.props.managementUrls.manageMemberships}
          className={classes.listItem}
        >
          <FontAwesomeIcon icon={faUsersCog} />&nbsp;
          <ListItemText primary={<FormattedMessage id="Membership" />} />
        </ListItem>
        )}
      </List>
    </Drawer>
  )
}

export const Nav = connect(mapStateToProps, mapDispatchToProps)(NavConnector)
