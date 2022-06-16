import React, { FC } from 'react'
import { useField } from 'formik'
import {
  Input as ChakraInput,
  InputProps as ChakraInputProps,
} from '@chakra-ui/react'


interface InputFieldProps extends ChakraInputProps {}

const InputField: FC<InputFieldProps> = (props) => {
  const { name } = props

  const [field, _meta, _helpers] = useField(name)

  /* eslint-disable react/jsx-props-no-spreading */
  return (
    <ChakraInput
      {...field}
      {...props}
    />
  )
  /* eslint-enable react/jsx-props-no-spreading */
}


export default InputField
