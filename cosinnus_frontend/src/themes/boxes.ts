import type { ComponentStyleConfig } from '@chakra-ui/theme'

export const Box: ComponentStyleConfig = {
  variants: {
    formBox: ({ colorMode }) => ({
      p: 5,
      border: '1px',
      bg: colorMode === "dark" ? "gray.600" : "white",
      w: '100%',
      borderColor: colorMode === "dark" ? "gray.600" : "gray.200",
      borderRadius: "base"
    }),
    fullheightMainColourBox: {
      bg: 'plattform.400',
      h: '100vh',
      w:'100%'
    },
    fullheightGrayColourBox: ({ colorMode }) => ({
      bg: colorMode === "dark" ? "black" : "gray.50",
      h: '100vh',
      w:'100%'
    }),
    errorAlert : {
      w: "100%",
      py: "3",
      px: "4",
      bg: "red.600",
      borderRadius: "base"
    }
  }
}