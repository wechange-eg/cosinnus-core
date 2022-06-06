import React from 'react'
import ReactDOM from 'react-dom'
import {Provider} from "react-redux"
import {
  ChakraProvider,
  ColorModeProvider,
  CSSReset}
from '@chakra-ui/react'
import { PersistGate } from 'redux-persist/integration/react'
import { persistStore } from 'redux-persist'
import { store} from "./store"
import App from "./components/App"
import theme from "./themes/themes"
import { ColorModeScript } from '@chakra-ui/react'

let persistor = persistStore(store);

ReactDOM.render(
  <Provider store={store}>
    <PersistGate loading={null} persistor={persistor}>
      <ChakraProvider theme={theme}>
          <App />
      </ChakraProvider>
    </PersistGate>
  </Provider>,
  document.getElementById("app")
)