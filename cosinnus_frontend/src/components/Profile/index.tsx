import React from "react"

import {
  Container,
  Center,
  Box,
  Button,
  Heading
} from '@chakra-ui/react'

import { logout } from "../../store/auth"
import { useAppDispatch, RootState } from "../../store"
import { useSelector } from 'react-redux'

export function ProfilePage() {

  const profile = useSelector((state: RootState) => state.profile);
  const dispatch = useAppDispatch();

  return (
    <Container maxW='2xl'>
      <Box mt={100} mb={5} px={5} pt={5} pb={100} border='1px' borderColor='gray.200'>
        <Center>
          <Box>
            {Object.keys(profile).length !== 0 &&
              <Heading>Hello {profile.user.username} </Heading>
            }
            <Center>
              <Button colorScheme="blue" onClick={() => dispatch(logout())}>LogOut</Button>
            </Center>
          </Box>
        </Center>
      </Box>
    </Container>
  )
}