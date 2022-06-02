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
  HStack,
  Grid,
  GridItem,
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
import { login } from "../../store/auth";
import { useAppDispatch, RootState } from "../../store"
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

        <Link><FormattedMessage id="Forgot your password?" /></Link>

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
}

export function LoginPage() {
  const errorMessage = useSelector((state: RootState) => state.auth.errorMessage);
  const accessToken = useSelector((state: RootState) => state.auth.accessToken);
  const dispatch = useAppDispatch();

  if (!!accessToken) {
    return <Redirect to="/" />;
  } else {
    return (
      <HStack spacing='0px'>
        <Box bg='gray.50' h='100vh' w='100%'>
          <Grid templateColumns='repeat(12, 1fr)' gap={0}>
            <GridItem colStart={4} colEnd={10} h='10'>
              <VStack spacing="4" align="start">
              <Center>
                <Heading>Anmelden</Heading>
                </Center>
                {errorMessage &&
                  <Alert status='error'>
                    <AlertIcon />
                    <AlertTitle>{errorMessage}</AlertTitle>
                  </Alert>
                }
              </VStack>
              <Box p={5} border='1px' bg="white" borderColor='gray.200'>
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
            </GridItem>
          </Grid>
        </Box>
        <Box bg='plattform.400' h='100vh' w='100%'></Box>
      </HStack>
    )
  }
}