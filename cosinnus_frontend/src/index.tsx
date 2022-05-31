import React from 'react'
import ReactDOM from 'react-dom'
import {Provider} from "react-redux"
import {ChakraProvider} from '@chakra-ui/react'
import {store} from "./rootStore"
import App from "./components/App"
import Theme from "./themes/themes"

ReactDOM.render(
  <Provider store={store}>
    <ChakraProvider theme={Theme}>
      <App />
    </ChakraProvider>
  </Provider>,
  document.getElementById("app")
)