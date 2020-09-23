import { createMuiTheme, lighten, darken } from "@material-ui/core"

import BrandonTextRegular from "./fonts/brandon-text-regular.ttf"
import BrandonTextItalic from "./fonts/brandon-text-italic.ttf"
import BrandonTextBold from "./fonts/brandon-text-bold.ttf"
import GramatikaMedium from "./fonts/gramatika-medium.woff"
import logo from "./images/logo.svg"

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

const gramatikaMedium = {
  fontFamily: "Gramatika Medium",
  fontStyle: "normal",
  fontDisplay: "swap",
  fontWeight: 400,
  src: `
    url(${GramatikaMedium}) format("otf")
  `
}

export const navWidth = "12vw"
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
    "h1 + p.MuiTypography-body1": {
      "margin-bottom": "2rem",
    },
    "@media only screen and (max-width: 959.95px)": {
      ".conference": {
        "margin-left": 0,
      }
    }
  }
}

export const theme = createMuiTheme({
  palette: {
    type: "light",
    primary: {
      main: "#7062b3",
      light: lighten("#7062b3", 0.5),
      contrastText: lighten("#7062b3", 0.75),
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
