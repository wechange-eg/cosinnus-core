import { makeStyles } from '@material-ui/core/styles'

export const useStyles = makeStyles((theme) => ({
  notification: {
    marginBottom: "1rem"
  },
  link: {
    color: theme.palette.text.primary,
    "&:hover": {
      color: theme.palette.text.primary
    }
  }
}));