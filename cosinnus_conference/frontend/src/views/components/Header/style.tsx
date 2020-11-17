import { makeStyles } from '@material-ui/core/styles'

import {navWidth} from "../../../themes/themes"

export const useStyles = makeStyles((theme) => ({
  header: {
    marginBottom: "1rem"
  },
  wallpaper: {
    display: "block",
    width: "100%",
    marginBottom: "1rem"
  },
  images: {
    flexWrap: "nowrap",
    // Promote the list into his own layer on Chrome. This cost memory but helps keeping high FPS.
    transform: "translateZ(0)",
  }
}));