import {Grid} from "@material-ui/core"
import { styled } from "@material-ui/core/styles"

export const Content = styled(Grid)(({ theme }) => ({
  flex: 1,
  padding: "2rem",
  minHeight: "100%",
  "& h1": {
    fontSize: "1rem",
    textTransform: "uppercase",
    fontWeight: "700",
    color: theme.palette.text.primary,
    marginBottom: "1rem",
  },
  "& a, & a:hover, & a:focus, & a:visited": {
    color: theme.palette.text.primary,
    fontWeight: "700",
  },
  "&.fullheight": {
    display: "flex",
    flexDirection: "column",
    "& > *": {
      flex: "0"
    },
    "& > .iframe": {
      flex: "1"
    }
  },
  [theme.breakpoints.down('sm')]: {
    width: "100%",
    flexBasis: "100%",
  },
}))
