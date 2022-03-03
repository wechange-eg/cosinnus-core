import { makeStyles } from '@material-ui/core/styles'

import {miniSidebarWidth, sidebarWidth} from "../../../themes/themes"

export const useStyles = makeStyles((theme) => ({
  buttons: {
    color: theme.palette.text.primary,
    "& > a, & > span > a": {
      color: theme.palette.text.primary,
      "&:hover,&:focus,&:active": {
        color: theme.palette.primary.main,
      }
    },
    '& > *': {
      margin: theme.spacing(1),
    },
  },
}))
