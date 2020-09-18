import React from "react"
import {
  ListItemText, Drawer, Typography, List, ListItem, Badge
} from "@material-ui/core"
import {connect} from "react-redux"
import {FontAwesomeIcon} from "@fortawesome/react-fontawesome"
import {
  faBuilding, faCheck,
  faCircle,
  faCoffee,
  faComments,
  faHandshake,
  faHome, faUser,
  faUsers
} from '@fortawesome/free-solid-svg-icons'

import {RootState} from "../../../stores/rootReducer"
import {useStyles} from "./style"
import {ConferenceState} from "../../../stores/conference/reducer"
import {IconDefinition} from "@fortawesome/fontawesome-common-types"

interface NavProps {
  conference: ConferenceState
}

function mapStateToProps(state: RootState) {
  return {
    conference: state.conference
  }
}

const mapDispatchToProps = {
}

function NavConnector(props: NavProps) {
  const { conference } = props
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
      "coffee-tables": faCoffee,
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
        <Typography component="h3">{conference.name}</Typography>
        <Typography component="h4">{conference.description}</Typography>
      </div>
      <List>
        {Object.keys(conference.rooms).map((key, index) => {
          const room = conference.rooms[key]
          return (
            <ListItem
              button
              key={key}
              href={"../" + key + "/"}
              selected={key === window.conferenceRoom}
              className={classes.listItem}
            >
              <FontAwesomeIcon icon={getIconByType(room.type)}/>&nbsp;
              <ListItemText primary={room.name}/>
              <Badge badgeContent={room.count} className={classes.badge} />
            </ListItem>
          )
        })}
      </List>
    </Drawer>
  )
}

export const Nav = connect(mapStateToProps, mapDispatchToProps)(NavConnector)
