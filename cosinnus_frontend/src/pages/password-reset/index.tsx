import React, { FC } from 'react'
import { useSelector } from 'react-redux'
import {
  Heading,
  Button,
  VStack,
  FormControl,
  FormLabel,
  Center,
  Text,
} from '@chakra-ui/react'
import {
  Formik,
  Form,
} from 'formik'

import { FormattedMessage } from 'react-intl'
import InputField from '../../components/shared/input'
import SplitColumns from '../../layouts/SplitColumns'
import StyledBox from '../../components/shared/boxes'

import { RootState } from '../../store'


const PasswordResetPage: FC = () => {
  const errorMessage = useSelector((state: RootState) => state.message.text)

  const getForm = ({ isSubmitting }: { isSubmitting: boolean }) => (
    <Form>
      <VStack spacing="4" align="start">
        <FormControl isRequired>
          <FormLabel htmlFor="email">Email address</FormLabel>
          <InputField name="email" type="email" />
        </FormControl>

        <Button
          type="submit"
          isLoading={isSubmitting}
          colorScheme="blue"
          width="100%"
          mb="1"
        >
          <FormattedMessage id="Request a password reset" />
        </Button>
      </VStack>
    </Form>
  )

  return (
    <SplitColumns>
      <Center w="100%">
        <Heading>
          <FormattedMessage id="Forgot password?" />
        </Heading>
      </Center>
      <Center w="100%">
        <Text align="center">
          <FormattedMessage id="We'll send you an email with a link to reset your password." />
        </Text>
      </Center>

      {errorMessage
        && (
        <StyledBox variant="errorAlert">
          <Text variant="white" fontWeight={700}>
            <FormattedMessage id="Password reset not possible" />
          </Text>
          <Text variant="white">{errorMessage}</Text>
        </StyledBox>
        )}

      <StyledBox variant="formBox">
        <Formik
          initialValues={{
            email: `${process.env.USER_EMAIL || ''}`,
          }}
          onSubmit={(values) => {
            console.log(values)
          }}
        >
          {getForm}
        </Formik>
      </StyledBox>
    </SplitColumns>
  )
}


export default PasswordResetPage
