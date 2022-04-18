import { AnyAction } from "redux"

import { ActionType } from "../../constants/actions"
import {Settings} from "./models"

export function SettingsReducer(
  state: Settings = null,
  action: AnyAction
): Settings {
  switch (action.type) {
    case ActionType.FETCH_SETTINGS_SUCCESS: {
      return action.payload
    }
    case ActionType.FETCH_SETTINGS_ERROR: {
      return state
    }
    default: {
      return state
    }
  }
}