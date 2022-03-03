import React from 'react'
import ReactDOM from 'react-dom'
import {Provider} from "react-redux"

import {rootStore} from "./stores/rootStore"
import {App} from "./views/App"

ReactDOM.render(
  <Provider store={rootStore}>
    <App />
  </Provider>,
  document.getElementById("app")
)