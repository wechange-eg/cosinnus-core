import React from 'react'
import ReactDOM from 'react-dom'
import {Provider} from "react-redux"
import {ChakraProvider} from '@chakra-ui/react'
import {rootStore} from "./stores/rootStore"
import {App} from "./views/App"
import Theme from "./themes/themes"

ReactDOM.render(
  <Provider store={rootStore}>
    <ChakraProvider theme={Theme}>
      <App />
    </ChakraProvider>
  </Provider>,
  document.getElementById("app")
)