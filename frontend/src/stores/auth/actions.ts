import {ActionType} from "../../constants/actions"
import {ReduxActionCreator, ReduxErrorActionCreator} from "../../utils/types"

export const setAuthToken: ReduxActionCreator<string> = authToken => ({
  type: ActionType.SET_AUTH_TOKEN,
  payload: authToken
})

export const setAuthError: ReduxErrorActionCreator<string> = loginError => ({
  type: ActionType.SET_AUTH_ERROR,
  payload: loginError ? Error(loginError) : null,
  error: !!loginError
})
