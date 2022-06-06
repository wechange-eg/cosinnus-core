import React from "react"
import { FieldHookConfig, useField } from "formik";
import {
  Input as ChakraInput,
  InputProps as ChakraInputProps,
} from "@chakra-ui/react";

type Props = ChakraInputProps & FieldHookConfig<"input">;

export const InputField = ({ name, ...props }: Props) => {
  const [field] = useField(name)
  return <ChakraInput {...props} {...field} />
}