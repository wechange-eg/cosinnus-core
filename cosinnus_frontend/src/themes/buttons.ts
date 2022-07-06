import type { ComponentStyleConfig } from '@chakra-ui/theme'

// todo: is plattform with two "t" a typo or intentional
const Button: ComponentStyleConfig = {
  baseStyle: ({ colorMode }) => ({
    background: colorMode === 'dark' ? 'plattform.300' : 'plattform.600',
    color: colorMode === 'dark' ? 'black' : 'white',
  }),
  defaultProps: {
    variant: 'plattform',
  },
}

export default Button
