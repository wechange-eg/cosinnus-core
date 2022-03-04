import { createMuiTheme, lighten } from "@material-ui/core"

export const getTheme = (primaryColor= "#7062b3") => createMuiTheme({
  palette: {
    type: "light",
    primary: {
      main: primaryColor,
      light: lighten(primaryColor, 0.5),
      contrastText: lighten(primaryColor, 0.75),
    },
    text: {
      primary: "#4a4a4a",
      secondary: "#929292"
    },
    background: {
      default: "#ffffff",
      paper: "#f2f2f2"
    },
    success: {
      main: "#3e806d"
    }
  },
  typography: {
    fontFamily: '"Brandon Text",sans-serif',
    fontWeight: 400,
    fontSize: 14,
    htmlFontSize: 14
  },
})

