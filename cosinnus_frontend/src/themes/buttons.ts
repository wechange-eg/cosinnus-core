import type { ComponentStyleConfig } from '@chakra-ui/theme'

export const Button: ComponentStyleConfig = {
  baseStyle: ({ colorMode }) => ({
    background: colorMode === "dark" ? "plattform.300" : "plattform.600",
    color: colorMode === "dark" ? "black" : "white"
  }),
  defaultProps: {
    variant: "plattform",
  },
}