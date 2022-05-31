import React from "react"

import {
  Container,
  Center,
  Box,
  Button,
  Heading
} from '@chakra-ui/react'

import { fetchUser } from "../../reducers/user"
import { logout } from "../../reducers/auth"
import { useAppDispatch, RootState } from "../../rootStore"
import { useSelector } from 'react-redux'
import { Redirect } from 'react-router-dom'


export function ProfilePage() {

  const user = useSelector((state: RootState) => state.user);
  const accessToken = useSelector((state: RootState) => state.auth.accessToken);
  const dispatch = useAppDispatch();
  dispatch(fetchUser())

  if (!accessToken) {
    return <Redirect to="/" />;
  } else {
    return (
      <Container maxW='2xl'>
        <Box mt={100} mb={5} px={5} pt={5} pb={100} border='1px' borderColor='gray.200'>
          <Center>
            {user &&
              <Box>
                <Heading>Hello {user.username}</Heading>
                <Center>
                  <Button colorScheme="blue" onClick={() => dispatch(logout())}>LogOut</Button>
                </Center>
              </Box>
            }
          </Center>
        </Box>
      </Container>
    )
  }
}