import React from "react"
import {CircularProgress} from "@material-ui/core"

import {useStyles} from "./style"

export function Loading() {
  const classes = useStyles()
  return (
    <div className={classes.progress}>
     <CircularProgress color="primary" />
    </div>
  )
}
