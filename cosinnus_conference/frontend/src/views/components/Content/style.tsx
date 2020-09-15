import {Grid} from "@material-ui/core"
import { styled } from "@material-ui/core/styles"

export const Content = styled(Grid)(({ theme }) => ({
  flex: 1,
  padding: "2rem",
  "& h1": {
    fontSize: "1rem",
    textTransform: "uppercase",
    fontWeight: "700",
    color: theme.palette.primary.main,
    marginBottom: "1rem",
  }
}))
