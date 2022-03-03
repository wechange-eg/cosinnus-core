import { makeStyles } from '@material-ui/core/styles';

export const useStyles = makeStyles((theme) => ({
  card: {
    background: theme.palette.primary.contrastText,
    width: "100%",
    marginBottom: "1rem",
    "& h3": {
      fontSize: "1rem",
      fontWeight: "bold",
      marginBottom: ".5rem",
    },
    "& img": {
      marginBottom: ".5rem",
    },
    "& > div  > div": {
      marginBottom: "1rem",
    },
    "& p": {
      textAlign: "right",
    },
    "&:hover": {
      background: theme.palette.primary.main,
      cursor: "pointer",
      color: theme.palette.text.secondary,
      "& div:first-child p": {
        color: theme.palette.primary.light,
      }
    }
  },
  participant: {
    height: "4.6rem",
    "& > span": {
      display: "block",
      background: theme.palette.primary.light,
      color: theme.palette.primary.main,
      padding: ".5rem",
      overflow: "hidden",
      borderRadius: ".3rem",
      height: "100%",
      "& span": {
        display: "block",
        fontWeight: "bold",
      }
    }
  },
  column: {
    flex: "50%",
  },
}));
