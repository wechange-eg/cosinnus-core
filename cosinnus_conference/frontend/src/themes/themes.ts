import { createMuiTheme, lighten } from "@material-ui/core"
var tinycolor = require("tinycolor2");

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
    ".announcement": {
      "margin-top": "0",
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

  // if the primary color is set too bright to be readable,
  // swith the secondary text color to dark
  if (tinycolor(primaryColor).getBrightness() > 200) {
      primaryText = "#4a4a4a" // regular flow text
      secondaryText = "#333333" // hovered and emphasized text
  }

  return createMuiTheme({
    palette: {
      type: "light",
      primary: {
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

