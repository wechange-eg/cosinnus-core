import React from "react"
import {
  ListItemText, Drawer, Typography, List, ListItem, Badge
} from "@material-ui/core"
import {connect} from "react-redux"
import {FontAwesomeIcon} from "@fortawesome/react-fontawesome"
import { faCircle } from '@fortawesome/free-solid-svg-icons'

import {RootState} from "../../../stores/rootReducer"
import {useStyles} from "./style"
import {ConferenceState} from "../../../stores/conference/reducer"

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
  if (!conference) {
    return null
  }
  const classes = useStyles()
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
        {conference.rooms.map((room, index) => (
          <ListItem
            button
            key={room.slug}
            href={"../" + room.slug + "/"}
            selected={room.slug === window.conferenceView}
            className={classes.listItem}
          >
            <FontAwesomeIcon icon={faCircle} />&nbsp;
            <ListItemText primary={room.name} />
            <Badge badgeContent={room.count} className={classes.badge} />
          </ListItem>
        ))}
      </List>
    </Drawer>
  )
}

export const Nav = connect(mapStateToProps, mapDispatchToProps)(NavConnector)
