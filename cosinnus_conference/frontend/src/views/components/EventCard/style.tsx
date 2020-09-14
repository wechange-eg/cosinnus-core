import { makeStyles } from '@material-ui/core/styles';

export const useStyles = makeStyles((theme) => ({
  card: {
    background: theme.palette.primary.contrastText,
    width: "100%",
    height: "10rem",
    marginBottom: "1rem",
    "& > div": {
      padding: "1rem",
      width: "100%",
      height: "100%",
      display: "flex",
    },
    "& span": {
      fontWeight: "bold",
      display: "block",
    },
    "&:hover": {
      background: theme.palette.primary.main,
      cursor: "pointer",
      color: "#ffffff",
      "& div:first-child p": {
        color: theme.palette.primary.light,
      }
    }
  },
  left: {
    flex: "60%",
    margin: "auto 0 0",
    "& p": {
      color: theme.palette.text.secondary,
    },
  },
  right: {
    flex: "40%",
    textAlign: "right",
    margin: "auto 0 0",
  },
  link: {
    color: theme.palette.text.secondary,
    marginLeft: ".5rem",
  }
}));
