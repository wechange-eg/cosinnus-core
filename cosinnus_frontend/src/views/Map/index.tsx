import React from "react"
import { connect } from "react-redux"
import { withRouter } from "react-router"

import { fetchUser } from "../../stores/user/effects"
import { logout } from "../../stores/auth/effects";

import {
  Container,
  Center,
  Box,
  Button,
  Heading
} from '@chakra-ui/react'

function mapStateToProps(state: any) {
  const { isLoggedIn } = state.auth;
  const { message } = state.message;
  const { user } = state

  return {
    isLoggedIn,
    message,
    user
  };
}

const mapDispatchToProps = {
  fetchUser,
  logout
}

export function MapConnector(props: any) {

  const { fetchUser, user, logout } = props
  if (!user) fetchUser()

  return (
    <Container maxW='2xl'>
      <Box mt={100} mb={5} px={5} pt={5} pb={100} border='1px' borderColor='gray.200'>
        <Center>
          {user &&
            <Box>
              <Heading>Hello {user.props.username}</Heading>
              <Center>
                <Button colorScheme="blue" onClick={logout}>LogOut</Button>
              </Center>
            </Box>
          }
        </Center>
      </Box>
    </Container>
  )
}

export const Map = connect(mapStateToProps, mapDispatchToProps)(
  withRouter(MapConnector)
)
