import { applyMiddleware, createStore } from "redux"
import thunk from "redux-thunk"

import { rootReducer } from "./rootReducer"

const rootStore = createStore(rootReducer, applyMiddleware(thunk))

export { rootStore }
