import { makeStyles } from '@material-ui/core/styles'

import {miniSidebarWidth, sidebarWidth} from "../../../themes/themes"

export const useStyles = makeStyles((theme) => ({
  drawer: {
    flexBasis: sidebarWidth,
    border: "none",
    padding: "2rem",
    overflowX: "visible",
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
    padding: "2rem",
    zIndex: 1,
    overflow: "visible",
    marginTop: "64px",
    overflowY: "scroll",
    backgroundColor: theme.palette.background.default,
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
    "& > div": {
      display: "none !important"
    }
  },
  button: {
    color: theme.palette.primary.main,
    fontWeight: "bold",
    position: "absolute",
    top: 0,
    left: "-1rem",
    borderRadius: 0,
    "& svg": {
      width: "auto"
    },
    "&:hover": {
      backgroundColor: "transparent",
      color: theme.palette.primary.light,
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
    width: "100%",
    height: "100%",
  },
}))
