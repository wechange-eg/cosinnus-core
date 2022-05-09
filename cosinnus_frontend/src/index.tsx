import React from 'react'
import ReactDOM from 'react-dom'
import {Provider} from "react-redux"
import { ChakraProvider } from '@chakra-ui/react'
import {rootStore} from "./stores/rootStore"
import {App} from "./views/App"

ReactDOM.render(
  <Provider store={rootStore}>
    <ChakraProvider>
      <App />
    </ChakraProvider>
  </Provider>,
  document.getElementById("app")
)