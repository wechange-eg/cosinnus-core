import React, { FC } from 'react'
import {
  Formik,
  Form,
} from 'formik'
import { FormattedMessage } from 'react-intl'
import {
  Box,
  Heading,
  Button,
  VStack,
  Text,
  FormControl,
  FormLabel,
  Link,
  Center,
} from '@chakra-ui/react'

import { Link as RouterLink } from 'react-router-dom'
import { useSelector } from 'react-redux'
import { StyledBox } from '../../shared/boxes'

import { InputField } from '../../shared/input'
import { TwoColumnPage } from '../../shared/pages'
import { login } from '../../../store/sessionAuth'
import { useAppDispatch, RootState } from '../../../store'

const getForm = ({ isSubmitting }: { isSubmitting: boolean }) => (
  <Form>
    <VStack spacing="4" align="start">
      <FormControl isRequired>
        <FormLabel htmlFor="username">Email address</FormLabel>
        <InputField name="username" type="email" autoComplete="off" />
      </FormControl>

      <FormControl isRequired>
        <FormLabel htmlFor="password">Password</FormLabel>
        <InputField name="password" type="password" />
      </FormControl>

      <Link variant="gray" as={RouterLink} to="/password-reset">
        <FormattedMessage id="Forgot your password?" />
      </Link>

      <Button
        type="submit"
        isLoading={isSubmitting}
        width="100%"
        mb="1"
      >
        <FormattedMessage id="Login" />
      </Button>
    </VStack>
  </Form>
)

const LoginPage: FC = () => {
  const errorMessage = useSelector((state: RootState) => state.message.text)
  useSelector((state: RootState) => state.sessionAuth.isLoggedIn)
  const dispatch = useAppDispatch()

  return (
    <TwoColumnPage>
      <Center w="100%">
        <Heading>
          <FormattedMessage id="Log In" />
        </Heading>
      </Center>
      <Center w="100%">
        <Text>
          <FormattedMessage id="Welcome to wechange.de" />
        </Text>
      </Center>
      {errorMessage
        && (
        <StyledBox variant="errorAlert">
          <Text variant="white" fontWeight={700}>
            <FormattedMessage id="Login not possible" />
          </Text>
          <Text variant="white">{errorMessage}</Text>
        </StyledBox>
        )}
      <StyledBox variant="formBox">
        <Formik
          initialValues={{
            username: `${process.env.USER_EMAIL || ''}`,
            password: `${process.env.USER_PASSWORD || ''}`,
          }}
          onSubmit={(values, { setSubmitting }) => {
            dispatch(login(values))
            setSubmitting(false)
          }}
        >
          {getForm}
        </Formik>
      </StyledBox>
      <Box>
        <Center>
          <Text>
            <FormattedMessage id="You don’t have an account?" />
          </Text>
        </Center>
        <Center>
          <Text>
            <Link as={RouterLink} to="/register">
              <FormattedMessage id="Sign Up" />
            </Link>
          </Text>
        </Center>
      </Box>
    </TwoColumnPage>
  )
}

export default LoginPage
