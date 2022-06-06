import type { ComponentStyleConfig } from '@chakra-ui/theme'

export const Input: ComponentStyleConfig = {
  baseStyle: {
    borderColor: "gray.900",
  },
  defaultProps: {
    variant: "outline",
    focusBorderColor: 'gray.900',
  },
}