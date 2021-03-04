import { makeStyles } from '@material-ui/core/styles';

export const useStyles = makeStyles((theme) => ({
  iframe: {
    height: "calc(100% - 2rem)",
    background: theme.palette.primary.contrastText,
    borderRadius: ".3rem",
    "& iframe": {
      border: "none",
      padding: ".5rem",
    }
  },
  fullscreen: {
    position: "fixed",
    top: 0,
    left: 0,
    width: "100%",
    height: "100%",
    zIndex: 100,
    "& > div > a:first-child": {
      display: "none"
    },
    "& > div > a": {
      position: "fixed",
      top: "4rem",
      right: "6rem",
      zIndex: 101,
      color: theme.palette.primary.main,
    }
  },
  buttons: {
    float: "right",
    marginTop: "-2.6rem",
    fontSize: "1.6rem",
    color: theme.palette.text.primary,
    width: "4rem",
    display: "flex",
    alignItems: "right",
    "& > a": {
      flex: 1,
      color: theme.palette.text.primary,
      "&:hover,&:focus,&:active": {
        color: theme.palette.primary.main,
      }
    }
  },
  newTabLink: {
  },
  fullScreenLink: {
  },
}));
