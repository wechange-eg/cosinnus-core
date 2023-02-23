import { makeStyles } from '@material-ui/core/styles'


export const useStyles = makeStyles((_theme) => ({
  icons: {
    position: "absolute",
    right: "2rem",
    bottom: ".5rem",
    textAlign: "right",
    "& > *": {
      marginLeft: "1rem",
      display: "inline-block !important",
    }
  }
}))
