import type { ComponentStyleConfig } from '@chakra-ui/theme'

const Heading: ComponentStyleConfig = {
  baseStyle: ({ colorMode }) => ({
    color: colorMode === 'dark' ? 'white' : 'gray.800',
  }),
  defaultProps: {
    size: 'md',
  },
}

export default Heading
