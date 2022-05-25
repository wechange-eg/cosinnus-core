import React from "react"
import { useHistory } from "react-router-dom"
import { connect } from "react-redux"
import {
  Formik,
  FormikBag,
  FormikValues,
  FormikProps,
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

import { Link as RouterLink } from 'react-router-dom'

import { LoginTextField } from "./style"
import { login } from "../../stores/auth/effects";

function mapStateToProps(state: any) {
  const { isLoggedIn } = state.auth;
  const { message } = state.message;
  return {
    isLoggedIn,
    message
  };
}

const mapDispatchToProps = {
  login
}

export function LoginConnector(props: any) {
  const history = useHistory();
  const { login, message } = props;

  const onSubmit = (
    values: FormikValues,
    formikBag: FormikBag<FormikProps<FormikValues>, FormikValues>
  ) => {
    login(values.email, values.password)
      .then(() => {
        history.push("/");
        formikBag.setSubmitting;
        window.location.reload();
      })
      .catch(() => {
        formikBag.setSubmitting(false)
      });
  }

  const getForm = ({ isSubmitting }: { isSubmitting: boolean }) => {
    return (
      <Form>
        <VStack spacing="4" align="start">
          <Heading>Anmelden</Heading>
          {message && !isSubmitting &&
            <Alert status='error'>
              <AlertIcon />
              <AlertTitle>{message}</AlertTitle>
            </Alert>
          }
          <FormControl isRequired>
            <FormLabel htmlFor='email'>Email address</FormLabel>
            <LoginTextField name="email" type="email" />
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
          <Text fontSize='xs'>Noch kein Account? <RouterLink to="/register">Registriere dich hier </RouterLink></Text>
        </Center>
      </Box>
    </Container>
  )
}

export const Login = connect(mapStateToProps, mapDispatchToProps)(LoginConnector)
