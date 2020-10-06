import { AnyAction } from "redux"

import { ActionType } from "../../constants/actions"

export interface ThemeState {
  color: number
}

export function ThemeReducer(
  state: ThemeState = null,
  action: AnyAction
): ThemeState {
  switch (action.type) {
    case ActionType.SET_THEME: {
      return action.payload
    }
    default: {
      return state
    }
  }
}
