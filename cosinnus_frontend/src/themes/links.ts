import type { ComponentStyleConfig } from '@chakra-ui/theme'

const Link: ComponentStyleConfig = {
  baseStyle: ({ colorMode }) => ({
    textDecoration: 'underline',
    color: colorMode === 'dark' ? 'white' : 'plattform.600',
  }),
  variants: {
    gray: ({ colorMode }) => ({
      color: colorMode === 'dark' ? 'white' : 'gray.800',
    }),
  },
  defaultProps: {
    variant: 'plattform',
  },
}

export default Link
