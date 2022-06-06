import React from "react"
import {
  Formik,
  Form
} from "formik"
import { FormattedMessage, useIntl } from "react-intl";
import {
  Box,
  Heading,
  Button,
  HStack,
  Grid,
  GridItem,
  VStack,
  Text,
  FormControl,
  FormLabel,
  Link,
  Center,
} from '@chakra-ui/react'

import { StyledBox } from "../shared/boxes";

import { Redirect, Link as RouterLink } from 'react-router-dom'
import { InputField } from "../shared/input"
import { login } from "../../store/auth";
import { useAppDispatch, RootState } from "../../store"
import { useSelector } from 'react-redux'

const getForm = ({ isSubmitting }: { isSubmitting: boolean }) => {
  return (
    <Form>
      <VStack spacing="4" align="start">
        <FormControl isRequired>
          <FormLabel htmlFor='username'>Email address</FormLabel>
          <InputField name="username" type="email" autoComplete="off"/>
        </FormControl>

        <FormControl isRequired>
          <FormLabel htmlFor='password'>Password</FormLabel>
          <InputField name="password" type="password" />
        </FormControl>

        <Link variant={"gray"}>
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
        <StyledBox variant={'fullheightGrayColourBox'} >
          <Grid templateColumns='repeat(12, 1fr)' gap={0} mt={32}>
            <GridItem mt={8} colStart={{ base: 1, md: 4 }} colEnd={{ base: 13, md: 10 }}>
              <VStack spacing="6" align="center">

                <Center w='100%' >
                  <Heading>
                    <FormattedMessage id="Log In" />
                  </Heading>
                </Center>

                <Center w='100%'>
                  <Text>
                    <FormattedMessage id="Welcome to wechange.de" />
                  </Text>
                </Center>

                {errorMessage &&
                  <StyledBox variant={'errorAlert'}>
                    <Text variant="white" fontWeight={700}>
                      <FormattedMessage id="Login not possible" />
                    </Text>
                    <Text variant="white">{errorMessage}</Text>
                  </StyledBox>
                }

                <StyledBox variant={'formBox'}>
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

              </VStack>
            </GridItem>
          </Grid>
        </StyledBox>
        <StyledBox variant={'fullheightMainColourBox'} w={{ base: '0px', lg: '100%'}}></StyledBox>
      </HStack>
    )
  }
}