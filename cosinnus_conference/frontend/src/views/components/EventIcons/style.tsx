import { makeStyles } from '@material-ui/core/styles'

import {miniSidebarWidth, sidebarWidth} from "../../../themes/themes"

export const useStyles = makeStyles((theme) => ({
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
