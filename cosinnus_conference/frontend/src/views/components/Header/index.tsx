import React, {useState} from "react"
import {
  ListItemText, Drawer, Typography, List, ListItem, Badge, Button, Divider, Link, Card, GridList, GridListTile
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

interface HeaderProps {
  conference: Conference
}

function mapStateToProps(state: RootState) {
  return {
    conference: state.conference
  }
}

const mapDispatchToProps = {
}

function HeaderConnector(props: HeaderProps) {
  const { conference } = props
  const classes = useStyles()
  if (!conference) {
    return null
  }
  if (!conference.props.wallpaper && (!conference.props.images || conference.props.images.length === 0)) {
    return null
  }
  return (
    <div className={classes.header}>
      {conference.props.wallpaper && (
        <img
          src={conference.props.wallpaper}
          alt={conference.props.name}
          className={classes.wallpaper}
        />
      )}
      <GridList className={classes.images} cols={6} spacing={20}>
        {conference.props.images.map((img) => (
          <GridListTile key={img}>
            <img src={img} alt="" />
          </GridListTile>
        ))}
      </GridList>
    </div>
  )
}

export const Header = connect(mapStateToProps, mapDispatchToProps)(HeaderConnector)
