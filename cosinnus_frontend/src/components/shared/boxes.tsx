import React, { FC } from 'react'
import { Box, useStyleConfig, BoxProps } from '@chakra-ui/react'


interface StyledBoxProps extends BoxProps{
  variant: any
}


const StyledBox: FC<StyledBoxProps> = (props) => {
  const { variant, ...boxProps } = props

  const styles = useStyleConfig('Box', { variant })

  return (
    // eslint-disable-next-line react/jsx-props-no-spreading
    <Box __css={styles} {...boxProps} />
  )
}


export default StyledBox
