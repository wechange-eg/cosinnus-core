import React from "react"
import {
  Formik,
  Form
} from "formik"
import { FormattedMessage, useIntl } from "react-intl";
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
  Center,
  Text
} from '@chakra-ui/react'

import { Redirect, Link as RouterLink } from 'react-router-dom'
import { LoginTextField } from "./style"
import { login } from "../../reducers/auth";
import { useAppDispatch, RootState } from "../../rootStore"
import { useSelector } from 'react-redux'

const getForm = ({ isSubmitting }: { isSubmitting: boolean }) => {
  return (
    <Form>
      <VStack spacing="4" align="start">
        <FormControl isRequired>
          <FormLabel htmlFor='username'>Email address</FormLabel>
          <LoginTextField name="username" type="email" />
        </FormControl>

        <FormControl isRequired>
          <FormLabel htmlFor='password'>Password</FormLabel>
          <LoginTextField name="password" type="password" />
        </FormControl>

        <Button
          type="submit"
          isLoading={isSubmitting}
          colorScheme="blue"
          width="100%"
          mb="1"
        >
          <FormattedMessage id="Login" />
        </Button>
        <Divider />
        <Link><FormattedMessage id="Forgot your password?" /></Link>
      </VStack>
    </Form>
  )
}

export function LoginPage() {
  const errorMessage = useSelector((state: RootState) => state.auth.errorMessage);
  const accessToken = useSelector((state: RootState) => state.auth.accessToken);
  const dispatch = useAppDispatch();

  if (!!accessToken) {
    return <Redirect to="/" />;
  } else {
    return (
      <Container maxW='2xl'>
        <Box mt={100} mb={5} px={5} pt={5} pb={100} border='1px' borderColor='gray.200'>
          <VStack spacing="4" align="start">
            <Heading>Anmelden</Heading>
            {errorMessage &&
              <Alert status='error'>
                <AlertIcon />
                <AlertTitle>{errorMessage}</AlertTitle>
              </Alert>
            }
          </VStack>
          <Formik
            initialValues={{
              username: `${process.env.USER_EMAIL || ""}`,
              password: `${process.env.USER_PASSWORD || ""}`
            }}
            onSubmit={(values, { setSubmitting }) => {
              dispatch(login(values))
              setSubmitting(false)
            }}
          >
            {getForm}
          </Formik>
        </Box>
        <Box>
          <Center>
            <Text fontSize='xs'>Noch kein Account? <RouterLink to="/register">Registriere dich hier </RouterLink></Text>
          </Center>
        </Box>
      </Container>
    )
  }
}