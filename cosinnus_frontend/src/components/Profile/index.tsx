import React from "react"

import {
  Container,
  Center,
  Box,
  Button,
  Heading
} from '@chakra-ui/react'

import { clearTokens } from "../../store/tokenAuth"
import { useAppDispatch, RootState } from "../../store"
import { useSelector } from 'react-redux'

export function ProfilePage() {

  const user = useSelector((state: RootState) => state.sessionAuth.user);
  const dispatch = useAppDispatch();

  return (
    <Container maxW='2xl'>
      <Box mt={100} mb={5} px={5} pt={5} pb={100} border='1px' borderColor='gray.200'>
        <Center>
          <Box>
            {Object.keys(user).length !== 0 &&
              <Heading>Hello {user.username} </Heading>
            }
            <Heading>Hello</Heading>
            <Center>
              <Button colorScheme="blue" onClick={() => dispatch(clearTokens())}>LogOut</Button>
            </Center>
          </Box>
        </Center>
      </Box>
    </Container>
  )
}