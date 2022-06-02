import React from 'react'
import ReactDOM from 'react-dom'
import {Provider} from "react-redux"
import {ChakraProvider} from '@chakra-ui/react'
import { PersistGate } from 'redux-persist/integration/react'
import { persistStore } from 'redux-persist'
import { store} from "./store"
import App from "./components/App"
import Theme from "./themes/themes"

let persistor = persistStore(store);

ReactDOM.render(
  <Provider store={store}>
    <PersistGate loading={null} persistor={persistor}>
      <ChakraProvider theme={Theme}>
        <App />
      </ChakraProvider>
    </PersistGate>
  </Provider>,
  document.getElementById("app")
)