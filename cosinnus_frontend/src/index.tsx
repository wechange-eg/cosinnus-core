import React from 'react'
import ReactDOM from 'react-dom'
import { Provider } from 'react-redux'
import { ChakraProvider } from '@chakra-ui/react'
import { PersistGate } from 'redux-persist/integration/react'
import { persistStore } from 'redux-persist'
import { store } from './store'
import App from './App'
import theme from './themes/themes'

const persistor = persistStore(store)

// todo: TS2786: 'PersistGate' cannot be used as a JSX component.
// the best guess is it's because of the outdated react version
// https://stackoverflow.com/questions/71826046/react-native-persistgate-cannot-be-used-as-a-jsx-component-its-instance-type
ReactDOM.render(
  <Provider store={store}>
    <PersistGate loading={null} persistor={persistor}>
      <ChakraProvider theme={theme}>
        <App />
      </ChakraProvider>
    </PersistGate>
  </Provider>,
  document.getElementById('app'),
)
