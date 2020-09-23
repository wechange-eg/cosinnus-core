import { makeStyles } from '@material-ui/core/styles'

import {miniSidebarWidth, sidebarWidth} from "../../../themes/themes"

export const useStyles = makeStyles((theme) => ({
  drawer: {
    flexBasis: sidebarWidth,
    border: "none",
    paddingTop: "100px",
    overflow: "visible",
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
  },
  button: {
    background: theme.palette.primary.main,
    color: "#ffffff",
    fontWeight: "bold",
    position: "absolute",
    top: "60px",
    left: "-1rem",
    "& svg": {
      marginRight: ".5rem",
    },
    "&:hover": {
      background: theme.palette.primary.light,
    }
  },
  iframe: {
    border: "none",
    borderLeft: "2px solid " + theme.palette.primary.main,
    width: "100%",
    height: "100%",
  },
}))
