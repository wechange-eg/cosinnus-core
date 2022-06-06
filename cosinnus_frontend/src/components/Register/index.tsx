import React from "react"
import { connect } from "react-redux"

import { Link as RouterLink } from 'react-router-dom'

import {
  Box,
  Heading,
  Button,
  VStack,
  FormControl,
  FormLabel,
  Center,
  Text,
  Link
} from '@chakra-ui/react'

import {
  Formik,
  Form
} from "formik"

import { FormattedMessage } from "react-intl";
import { InputField } from "../shared/input"
import { TwoColumnPage } from "../shared/pages"
import { StyledBox } from "../shared/boxes";

import { RootState } from "../../store"
import { useSelector } from 'react-redux'


export function RegisterPage() {
  const errorMessage = useSelector((state: RootState) => state.auth.errorMessage);

  const getForm = ({ isSubmitting }: { isSubmitting: boolean }) => {
    return (
      <Form>
        <VStack spacing="4" align="start">
          <FormControl isRequired>
            <FormLabel htmlFor='email'>Email address</FormLabel>
            <InputField name="email" type="email" />
          </FormControl>

          <FormControl isRequired>
            <FormLabel htmlFor='password'>Password</FormLabel>
            <InputField name="password" type="password" />
          </FormControl>

          <FormControl isRequired>
            <FormLabel htmlFor='passwordrepeat'>Password wiederholen</FormLabel>
            <InputField name="passwordrepeat" type="password" />
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
    <TwoColumnPage>

      <Center w='100%' >
        <Heading>
          <FormattedMessage id="Register" />
        </Heading>
      </Center>

      {errorMessage &&
        <StyledBox variant={'errorAlert'}>
          <Text variant="white" fontWeight={700}>
            <FormattedMessage id="Register not possible" />
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
            console.log(values)
          }}
        >
          {getForm}
        </Formik>
      </StyledBox>

      <Box>
        <Center>
          <Text>
            <FormattedMessage id="Already registered?" />
          </Text>
        </Center>
        <Center>
          <Text>
            <Link as={RouterLink} to="/login">
              <FormattedMessage id="Log In" />
            </Link>
          </Text>
        </Center>
      </Box>

    </TwoColumnPage>
  )
}
