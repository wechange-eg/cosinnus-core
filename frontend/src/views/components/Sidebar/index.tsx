import React, {useState} from "react"
import clsx from "clsx"
import {Button, Drawer, Grid} from "@material-ui/core"
import {FormattedMessage} from "react-intl"
import {FontAwesomeIcon} from "@fortawesome/react-fontawesome"
import {faChevronRight, faChevronLeft} from "@fortawesome/free-solid-svg-icons"
import Iframe from "react-iframe"

import {useStyles} from "./style"

interface SidebarProps {
  children: any
}

export function Sidebar(props: SidebarProps) {
  const { children } = props
  const [open, setOpen] = useState(true)
  const classes = useStyles()

  return (
    <Drawer
      variant="permanent"
      anchor="right"
      className={clsx(classes.drawer, {
        [classes.drawerOpen]: open,
        [classes.drawerClose]: !open,
      })}
      classes={{
        paper: clsx(classes.drawerPaper, {
          [classes.drawerPaperOpen]: open,
          [classes.drawerPaperClose]: !open,
        }),
      }}
    >
      <Button onClick={() => setOpen(!open)} className={classes.button}>
        <FontAwesomeIcon icon={open && faChevronRight || faChevronLeft} />
      </Button>
      {children}
    </Drawer>
  )
}
