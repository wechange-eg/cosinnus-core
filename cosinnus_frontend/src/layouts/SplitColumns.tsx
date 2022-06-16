import React, { FC } from 'react'
import {
  HStack,
  VStack,
  Grid,
  GridItem,
} from '@chakra-ui/react'
import StyledBox from '../components/shared/boxes'


const TwoColumnPage: FC = (props) => {
  const { children } = props

  return (
    <HStack spacing="0px">
      <StyledBox variant="fullheightGrayColourBox">
        <Grid templateColumns="repeat(12, 1fr)" gap={0} mt={32}>
          <GridItem mt={8} colStart={{ base: 1, md: 4 }} colEnd={{ base: 13, md: 10 }}>
            <VStack spacing="6" align="center">
              {children}
            </VStack>
          </GridItem>
        </Grid>
      </StyledBox>
      <StyledBox variant="fullheightMainColourBox" w={{ base: '0px', lg: '100%' }} />
    </HStack>
  )
}


export default TwoColumnPage
