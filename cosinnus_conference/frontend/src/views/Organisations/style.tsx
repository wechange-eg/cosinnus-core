import { makeStyles } from '@material-ui/core/styles';

export const useStyles = makeStyles((theme) => ({
  card: {
    background: theme.palette.primary.contrastText,
    width: "100%",
    "& > div": {
      padding: "1rem",
      paddingBottom: "1rem !important",
      width: "100%",
      height: "100%",
      display: "flex",
      flexDirection: "column",
      justifyContent: "center"
    },
    "& span": {
      fontWeight: "bold",
      display: "block",
      textTransform: "uppercase",
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
}));
