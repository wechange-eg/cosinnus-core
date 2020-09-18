import React from "react"
import {
  ListItemText, Drawer, Typography, List, ListItem, Badge, Button
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
  faUsers
} from '@fortawesome/free-solid-svg-icons'
import {IconDefinition} from "@fortawesome/fontawesome-common-types"

import {RootState} from "../../../stores/rootReducer"
import {useStyles} from "./style"
import {Room} from "../../../stores/room/models"
import {Conference} from "../../../stores/conference/models"
import {FormattedMessage} from "react-intl"

interface NavProps {
  conference: Conference
  room: Room
}

function mapStateToProps(state: RootState) {
  return {
    conference: state.conference,
    room: state.room,
  }
}

const mapDispatchToProps = {
}

function NavConnector(props: NavProps) {
  const { conference, room } = props
  const classes = useStyles()
  if (!conference) {
    return null
  }
  function getIconByType(type: string) {
    const icons: { [t: string]: IconDefinition } = {
      "lobby": faHome,
      "stage": faUser,
      "discussions": faComments,
      "workshops": faUsers,
      "coffee_tables": faCoffee,
      "networking": faHandshake,
      "exhibition": faBuilding,
      "results": faCheck,
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
              <ListItemText primary={navRoom.props.title}/>
              <Badge badgeContent={navRoom.props.count} className={classes.badge} />
            </ListItem>
        ))}
      </List>
      {conference.props.managementUrl && (
      <Button
        variant="contained"
        color="primary"
        disableElevation
        href="#"
        onClick={() => window.location.href = conference.props.managementUrl}
      >
        <FontAwesomeIcon icon={faCog} />&nbsp;
        <FormattedMessage id="Manage conference" defaultMessage="Manage conference" />
      </Button>
      )}
    </Drawer>
  )
}

export const Nav = connect(mapStateToProps, mapDispatchToProps)(NavConnector)
