import { makeStyles } from '@material-ui/core/styles'

import {navWidth} from "../../../themes/themes"

export const useStyles = makeStyles((theme) => ({
  drawer: {
    width: navWidth,
    [theme.breakpoints.down('sm')]: {
      width: "100%",
      flexBasis: "100%",
    },
  },
  drawerPaper: {
    backgroundColor: theme.palette.primary.main,
    border: "none",
    color: "#c3bdde",
    marginTop: "50px",
    width: navWidth,
    zIndex: 1,
    padding: "1.5rem 1rem 1.5rem 1.5rem",
    [theme.breakpoints.down('sm')]: {
      width: "100%",
      position: "static",
      marginTop: 0,
    },
  },
  drawerHeader: {
    marginBottom: "2rem",
    "& h3": {
      fontWeight: 700,
      color: "#ffffff",
      textTransform: "uppercase",
      fontSize: "1.4rem",
      marginBottom: "1rem"
    },
    "& h4": {
      fontWeight: "normal",
      fontSize: "1.2rem",
    },
  },
  listItem: {
    borderRadius: ".3rem",
    padding: ".1rem .5rem",
    marginBottom: "1.2rem",
    "& div": {
      whiteSpace: "nowrap",
      overflow: "hidden",
      textOverflow: "ellipsis",
    },
    "& svg": {
      width: "2rem !important",
    },
    "& span": {
      fontWeight: 700,
      fontSize: "1rem",
    },
    "& p": {
      color: theme.palette.primary.light,
    },
    "&:hover,&.Mui-selected,&.Mui-selected:hover": {
      background: "#ffffff",
      "& span,svg": {
        color: theme.palette.primary.main,
      },
      "&::after": {
        content: '" "',
        display: "block",
        background: theme.palette.primary.light,
        position: "absolute",
        right: "-1.5rem",
        width: "1rem",
        height: "100%",
        borderRadius: ".3rem 0 0 .3rem"
      }
    },
  },
  badge: {
    minWidth: "1rem",
    "& span": {
      fontWeight: 300,
      fontSize: ".8rem",
      right: ".5rem",
      color: theme.palette.primary.light
    }
  },
  toggleMenuButton: {
    fontSize: "1rem",
    color: theme.palette.primary.light,
    marginTop: "1rem",
    display: "block",
    [theme.breakpoints.up('sm')]: {
      display: "none"
    },
  },
  collapsed: {
    [theme.breakpoints.down('sm')]: {
      display: "none"
    },
  }
}));