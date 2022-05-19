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
  FormHelperText,
  Center,
  Text
} from '@chakra-ui/react'

import { LoginTextField } from "./style"
import { setAuthError } from "../../../stores/auth/actions"
import { RootState } from "../../../stores/rootReducer"
import { DispatchedReduxThunkActionCreator } from "../../../utils/types"
import { fetchAuthToken } from "../../../stores/auth/effects"
import { Settings } from "../../../stores/settings/models";

interface LoginProps {
  authError: string | null
  setAuthError: typeof setAuthError
  settings: Settings
  fetchAuthToken: DispatchedReduxThunkActionCreator<Promise<void>>
}

const mapStateToProps = (state: RootState) => ({
  authError: state.auth.error,
  settings: state.settings
})

const mapDispatchToProps = {
  setAuthError: setAuthError,
  fetchAuthToken
}

export function LoginConnector(props: LoginProps) {
  const { authError } = props;
  const { setAuthError, fetchAuthToken } = props;
  const { settings } = props;

  const history = useHistory();
  const intl = useIntl();
  let errorPrompt: React.ReactElement | null = null

  if (authError != null) {
    errorPrompt = (
      <FormattedMessage id={authError} />
    )
  }

  const onSubmit = (
    values: FormikValues,
    formikBag: FormikBag<FormikProps<FormikValues>, FormikValues>
  ) => {
    setAuthError(null)
    fetchAuthToken(
      values.email,
      values.password,
      formikBag.setSubmitting,
      () => {
        history.push("/")
      }
    )
  }

  const getForm = ({ isSubmitting }: { isSubmitting: boolean }) => {
    return (
      <Form>
          <VStack spacing="4" align="start">
            <Heading>Anmelden</Heading>
              { errorPrompt && !isSubmitting &&
              <Alert status='error'>
                <AlertIcon />
                <AlertTitle>{errorPrompt}</AlertTitle>
              </Alert>
              }
              <FormControl isRequired>
                <FormLabel htmlFor='email'>Email address</FormLabel>
                <LoginTextField name="email" type="email" />
                <FormHelperText>We'll never share your email.</FormHelperText>
              </FormControl>

              <FormControl isRequired>
                <FormLabel htmlFor='password'>Password</FormLabel>
                <LoginTextField name="password" type="password"/>
                <FormHelperText>We'll never share your email.</FormHelperText>
              </FormControl>

              <Button
                type="submit"
                isLoading={isSubmitting}
                colorScheme='blue'
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
          <Text fontSize='xs'>Noch kein Account? <Link>Registriere dich hier</Link></Text>
        </Center>
      </Box>
    </Container>
  )
}

export const Login = connect(mapStateToProps, mapDispatchToProps)(LoginConnector)
