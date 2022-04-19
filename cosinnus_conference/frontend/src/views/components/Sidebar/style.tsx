import { makeStyles } from '@material-ui/core/styles'

import {miniSidebarWidth, sidebarWidth} from "../../../themes/themes"

export const useStyles = makeStyles((theme) => ({
  drawer: {
    flexBasis: sidebarWidth,
    border: "none",
    paddingTop: "100px",
    overflow: "visible",
    [theme.breakpoints.down('sm')]: {
      width: "100% !important",
      flexBasis: "100% !important",
      position: "relative",
      padding: "2rem",
    },
  },
  drawerOpen: {
    flexBasis: sidebarWidth,
    transition: theme.transitions.create('flex-basis', {
      easing: theme.transitions.easing.sharp,
      duration: theme.transitions.duration.leavingScreen,
    }),
  },
  drawerClose: {
    flexBasis: miniSidebarWidth,
    transition: theme.transitions.create('flex-basis', {
      easing: theme.transitions.easing.sharp,
      duration: theme.transitions.duration.leavingScreen,
    }),
  },
  drawerPaper: {
    width: sidebarWidth,
    border: "none",
    paddingTop: "100px",
    zIndex: 1,
    overflow: "visible",
    background: theme.palette.primary.main,
    [theme.breakpoints.down('sm')]: {
      width: "100% !important",
      position: "static",
      marginTop: 0,
      height: "100vh",
      padding: 0,
    },
  },
  drawerPaperOpen: {
    width: sidebarWidth,
    transition: theme.transitions.create('width', {
      easing: theme.transitions.easing.sharp,
      duration: theme.transitions.duration.enteringScreen,
    }),
  },
  drawerPaperClose: {
    width: miniSidebarWidth,
    transition: theme.transitions.create('width', {
      easing: theme.transitions.easing.sharp,
      duration: theme.transitions.duration.leavingScreen,
    }),
    "& iframe": {
      display: "none !important"
    }
  },
  button: {
    background: theme.palette.primary.main,
    color: theme.palette.text.secondary,
    fontWeight: "bold",
    position: "absolute",
    top: "60px",
    left: "-1rem",
    "& svg": {
      marginRight: ".5rem",
    },
    "&:hover": {
      background: theme.palette.primary.light,
    },
    [theme.breakpoints.down('sm')]: {
      top: "-.4rem",
      left: "2rem",
      "& svg": {
        display: "none",
      },
      "&:hover": {
        background: theme.palette.primary.main,
      },
    },
  },
  iframe: {
    border: "none",
    borderLeft: "2px solid " + theme.palette.primary.main,
    width: "100%",
    height: "100%",
    [theme.breakpoints.down('sm')]: {
      border: "2px solid " + theme.palette.primary.main,
    }
  },
}))
