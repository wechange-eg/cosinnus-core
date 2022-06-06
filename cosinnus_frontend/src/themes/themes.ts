import {  extendTheme, ThemeConfig } from "@chakra-ui/react"

import { Button } from "./buttons"
import { Input } from "./forms"
import { Link } from "./links"
import { Heading } from "./headings"
import { Text } from "./texts"
import { Box } from "./boxes"

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
  black: "#212122",
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

const fontSizes = {
  xs: "0.75rem",
  sm: "0.875rem",
  md: "1rem",
  lg: "1.125rem",
  xl: "1.25rem",
  "2xl": "1.5rem",
  "3xl": "1.875rem",
  "4xl": "2.25rem",
  "5xl": "3rem",
  "6xl": "3.75rem",
  "7xl": "4.5rem",
  "8xl": "6rem",
  "9xl": "8rem",
}

const config: ThemeConfig = {
  initialColorMode: "light",
  useSystemColorMode: true
}

const theme = extendTheme({
  components: {
    Button,
    Input,
    Link,
    Heading,
    Text,
    Box
  },
  colors: wechangeColours,
  config,
})

export default theme