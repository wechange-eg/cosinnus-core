import React from "react"
import { Box, useStyleConfig } from '@chakra-ui/react'

export function StyledBox(props: any) {
    const { variant, ...rest } = props
    const styles = useStyleConfig('Box', { variant })
    return <Box __css={styles} {...rest} />
}