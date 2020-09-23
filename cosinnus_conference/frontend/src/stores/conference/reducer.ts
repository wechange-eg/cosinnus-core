import { AnyAction } from "redux"

import { ActionType } from "../../constants/actions"
import {Conference} from "./models"

export function ConferenceReducer(
  state: Conference = null,
  action: AnyAction
): Conference {
  switch (action.type) {
    case ActionType.FETCH_CONFERENCE_SUCCESS: {
      return action.payload
    }
    case ActionType.FETCH_CONFERENCE_ERROR: {
      return state
    }
    default: {
      return state
    }
  }
}