import { makeStyles } from '@material-ui/core/styles';

export const useStyles = makeStyles((theme) => ({
  card: {
    "& h1": {
      fontSize: "1.2rem"
    },
    "& *": {
      fontFamily: theme.typography.fontFamily
    }
  },
  media: {
    backgroundColor: theme.palette.primary.light,
    height: "16rem",
    position: "relative"
  },
  icon: {
    position: "absolute",
    width: "8rem",
    height: "8rem",
    bottom: "1rem",
    left: "1rem"
  },
  actionArea: {
  },
  focusHighlight: {
  },
}));
