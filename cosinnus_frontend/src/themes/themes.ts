import { extendTheme } from "@chakra-ui/react"

import { Button } from "./buttons"
import { Input } from "./forms"

const wechangeColours = {
  plattform: {
    main: "#7bb9e8",
    50: "#D7FCFC",
    100: "#A0EBE9",
    200: "#6FD9D5",
    300: "#00C7BD",
    400: "#1FB4A9",
    500: "#169C90",
    600: "#098276",
    700: "#02695D",
    800: "#004F45",
    900: "#00362E"
  },
  black: '#000',
  white: '#fff',
  gray: {
    50: "#F9FAFA",
    100: "#E2E3E4",
    200: "#C6C8CB",
    300: "#A7ABB0",
    400: "#8C8F95",
    500: "#74767B",
    600: "#5F6064",
    700: "#4B4C4F",
    800: "#3A3A3C",
    900: "#212122"
  },
}


const theme = extendTheme({
  colors: wechangeColours,
  components: {
    Button: Button,
    Input: Input
  }
})

export default theme