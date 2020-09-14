import { AnyAction } from "redux"

import { ActionType } from "../../constants/actions"
import {EventSlot} from "../events/models"

export function WorkshopsReducer(
  state: EventSlot[] = null,
  action: AnyAction
): EventSlot[] {
  switch (action.type) {
    case ActionType.FETCH_WORKSHOPS_SUCCESS: {
      return action.payload
    }
    case ActionType.FETCH_WORKSHOPS_ERROR: {
      return state
    }
    default: {
      return state
    }
  }
}
