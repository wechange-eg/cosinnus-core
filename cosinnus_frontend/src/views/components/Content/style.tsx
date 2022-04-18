import {Grid} from "@material-ui/core"
import { styled } from "@material-ui/core/styles"

export const Content = styled(Grid)(({ theme }) => ({
  flex: 1,
  padding: "2rem",
  minHeight: "100%",
  overflow: "hidden",
  "& h1": {
    fontSize: "1rem",
    textTransform: "uppercase",
    fontWeight: "700",
    color: theme.palette.primary.main,
    marginBottom: "1rem",
  },
  "&.fullheight": {
    display: "flex",
    flexDirection: "column",
    padding: 0,
    "& > *": {
      flex: 1
    },
  },
  [theme.breakpoints.down('sm')]: {
    width: "100%",
    flexBasis: "100%",
  },
}))
