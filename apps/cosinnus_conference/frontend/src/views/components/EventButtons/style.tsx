import { makeStyles } from '@material-ui/core/styles'

import {miniSidebarWidth, sidebarWidth} from "../../../themes/themes"

export const useStyles = makeStyles((theme) => ({
  buttons: {
    '& > *': {
      margin: theme.spacing(1),
    }
  }
}))
