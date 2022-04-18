import { AnyAction } from "redux"

import { ActionType } from "../../constants/actions"

export interface AuthState {
  token: string
  error?: string
}

export function AuthReducer(
  state: AuthState = { token: null },
  action: AnyAction
): AuthState {
  switch (action.type) {
    case ActionType.SET_AUTH_TOKEN: {
      return {
        token: action.payload
      }
    }
    case ActionType.SET_AUTH_ERROR: {
      return {
        token: null,
        error: action.payload ? action.payload.message : null
      }
    }
    default: {
      return state
    }
  }
}
