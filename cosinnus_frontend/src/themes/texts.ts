import type { ComponentStyleConfig } from '@chakra-ui/theme'

const Text: ComponentStyleConfig = {
  baseStyle: ({ colorMode }) => ({
    color: colorMode === 'dark' ? 'white' : 'gray.800',
    fontSize: 'md',
  }),
  variants: {
    white: {
      color: 'white',
    },
  },
}

export default Text
