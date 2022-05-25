import React from "react"
import { connect } from "react-redux"

import { Link as RouterLink } from 'react-router-dom'

import {
  Container,
  Box,
  Heading,
  Button,
  VStack,
  Divider,
  Alert,
  AlertIcon,
  AlertTitle,
  FormControl,
  FormLabel,
  Link,
  FormHelperText,
  Center,
  Text
} from '@chakra-ui/react'

import {
  Formik,
  FormikBag,
  FormikValues,
  FormikProps,
  Form
} from "formik"

import { FormattedMessage } from "react-intl";

import { RootState } from "../../stores/rootReducer"
import { setAuthError } from "../../stores/auth/actions"

import { LoginTextField } from "../Login/style"

const mapStateToProps = (state: RootState) => ({
  authError: state.auth.error,
  settings: state.settings
})

const mapDispatchToProps = {
  setAuthError: setAuthError
}


export function RegisterConnector() {

  const onSubmit = (
    values: FormikValues,
    formikBag: FormikBag<FormikProps<FormikValues>, FormikValues>
  ) => {
    alert(values)
  }

  const getForm = ({ isSubmitting }: { isSubmitting: boolean }) => {
    return (
      <Form>
          <VStack spacing="4" align="start">
            <Heading>Register</Heading>
              <FormControl isRequired>
                <FormLabel htmlFor='email'>Email address</FormLabel>
                <LoginTextField name="email" type="email" />
              </FormControl>

              <FormControl isRequired>
                <FormLabel htmlFor='password'>Password</FormLabel>
                <LoginTextField name="password" type="password"/>
              </FormControl>

              <FormControl isRequired>
                <FormLabel htmlFor='passwordrepeat'>Password wiederholen</FormLabel>
                <LoginTextField name="passwordrepeat" type="password"/>
              </FormControl>

              <Button
                type="submit"
                isLoading={isSubmitting}
                colorScheme='blue'
                width="100%"
                mb="1"
              >
                <FormattedMessage id="Register" />
              </Button>
          </VStack>
      </Form>
    )
  }

  return (
    <Container maxW='2xl'>
      <Box mt={100} mb={5} px={5} pt={5} pb={100} border='1px' borderColor='gray.200'>
      <Formik
          initialValues={{
            email: `${process.env.USER_EMAIL || ""}`,
            password: `${process.env.USER_PASSWORD || ""}`
          }}
          onSubmit={onSubmit}
        >
          {getForm}
        </Formik>
      </Box>
      <Box>
        <Center>
          <Text fontSize='xs'>Schon registiriert? <RouterLink to="/login">Hier anmelden</RouterLink></Text>
        </Center>
      </Box>
    </Container>
  )
}

export const Register = connect(mapStateToProps, mapDispatchToProps)(RegisterConnector)
