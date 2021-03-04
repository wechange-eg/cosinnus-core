import { createMuiTheme, lighten, darken } from "@material-ui/core"

import BrandonTextRegular from "./fonts/brandon-text-regular.ttf"
import BrandonTextItalic from "./fonts/brandon-text-italic.ttf"
import BrandonTextBold from "./fonts/brandon-text-bold.ttf"

const brandonTextRegular = {
  fontFamily: "Brandon Text",
  fontStyle: "normal",
  fontDisplay: "swap",
  fontWeight: 400,
  src: `
    url(${BrandonTextRegular}) format("ttf")
  `
}

const brandonTextItalic = {
  fontFamily: "Brandon Text",
  fontStyle: "italic",
  fontDisplay: "swap",
  fontWeight: 400,
  src: `
    url(${BrandonTextItalic}) format("ttf")
  `
}

const brandonTextBold = {
  fontFamily: "Brandon Text",
  fontStyle: "normal",
  fontDisplay: "swap",
  fontWeight: 700,
  src: `
    url(${BrandonTextBold}) format("ttf")
  `
}

export const navWidth = "14vw"
export const sidebarWidth = "30vw"
export const miniSidebarWidth = "5vw"

const muiCssBaseline = {
  "@global": {
    "@font-face": [
      brandonTextRegular,
      brandonTextItalic,
      brandonTextBold
    ],
    "html": {
      "font-size": "14px",
      "height": "100%"
    },
    "body": {
      "padding-top": "50px",
      "background": "#ffffff",
      "height": "100%",
    },
    ".conference": {
      "margin-left": navWidth,
      "height": "100%",
    },
    "p": {
      "padding": 0,
      "background": "transparent",
    },
    "#app": {
      "height": "100%",
    },
    "h1 + .description": {
      "margin-bottom": "2rem",
    },
    "@media only screen and (max-width: 959.95px)": {
      ".conference": {
        "margin-left": 0,
      }
    }
  }
}


export const getTheme = (primaryColor= "#7062b3") => {
  var primaryText = "#4a4a4a" // regular flow text
  var secondaryText = "#ffffff" // hovered and emphasized text
  var shift = lighten
  if (true) {
      primaryText = "#4a4a4a"
      secondaryText = "#333333"
      //shift = darken
  }

  return createMuiTheme({
    palette: {
      type: "light",
      primary: {
        main: primaryColor,
        light: shift(primaryColor, 0.5),
        contrastText: shift(primaryColor, 0.75),
      },
      secondary: {
        main: primaryColor,
        light: lighten(primaryColor, 0.5),
        contrastText: lighten(primaryColor, 0.75),
      },
      text: {
        primary: primaryText,
        secondary: secondaryText,
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
    overrides: {
      MuiCssBaseline: muiCssBaseline,
      MuiTypography: {
        body1: {
          fontSize: "1rem"
        }
      },
      MuiFilledInput: {
        root: {
          backgroundColor: "rgba(0, 0, 0, 0)"
        }
      }
    },
    shadows: Array(25).fill("none")
  })
}

